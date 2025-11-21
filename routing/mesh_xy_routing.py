import re
import os
import sys
from mininet.net import Mininet
from mininet.node import OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from topology.mesh_topology import MeshTopology

SWITCH_REGEX = re.compile(r"s(\d+)x(\d+)$")
HOST_REGEX = re.compile(r"h(\d+)x(\d+)$")

def coord_from_name(name, is_switch = True):
    regex = SWITCH_REGEX if is_switch else HOST_REGEX
    res = regex.match(name)
    if not res:
        raise ValueError(f"'{name}' is not a valid host/switch name")
    return int(res.group(1)), int(res.group(2))

def build_coord_maps(net):
    switch_coord_map = {}
    host_coord_map = {}

    for s in net.switches:
        coord = coord_from_name(s.name, is_switch=True)
        switch_coord_map[coord] = s

    for h in net.hosts:
        coord = coord_from_name(h.name, is_switch=False)
        host_coord_map[coord] = h

    return switch_coord_map, host_coord_map

def port_to_neighbor(switch, neighbor):
    links = switch.connectionsTo(neighbor)
    if not links:
        raise Exception(f"Link from {switch.name} to {neighbor.name} doesn't exist")
    interface = links[0][0]
    return switch.ports[interface]

def build_ports_map(net, switch_coord_map, host_coord_map):
    ports = {}
    coords = sorted(switch_coord_map.keys())

    for (i, j) in coords:
        switch = switch_coord_map[(i, j)]
        ports[(i, j)] = {}

        host = host_coord_map[(i, j)]
        ports[(i, j)]['host'] = port_to_neighbor(switch, host)

        neighbors = {'up': (i - 1, j), 'down': (i + 1, j), 'left': (i, j - 1), 'right': (i, j + 1)}

        for direction, coords in neighbors.items():
            if coords in switch_coord_map:
                neighbor_switch = switch_coord_map[coords]
                ports[(i, j)][direction] = port_to_neighbor(switch, neighbor_switch)

            else:
                ports[(i, j)][direction] = None

    return ports

def build_arp(host_coord_map):
    coords = list(host_coord_map.keys())

    for src_coords in coords:
        h1 = host_coord_map[src_coords]

        for dst_coords in coords:
            if src_coords == dst_coords:
                continue

            h2 = host_coord_map[dst_coords]
            h1.setARP(ip = h2.IP(), mac = h2.MAC())

def build_xy_routes(ports, switch_coord_map, host_coord_map):
    info("*** Building X–Y routing flows\n")
    for (dx, dy), h_dest in host_coord_map.items():
        dest_ip = h_dest.IP()

        for (x, y), switch in switch_coord_map.items():
            if (x, y) == (dx, dy):
                out_port = ports[(x, y)]['host']

            else:
                if x != dx:
                    direction = 'down' if dx > x else 'up'
                else:
                    direction = 'right' if dy > y else 'left'

                out_port = ports[(x, y)][direction]

                if out_port is None:
                    raise Exception(f"Closed port for direction {direction} from switch ({x},{y}) to ({dx},{dy})")

            flow = f"priority=100,ip,nw_dst={dest_ip},actions=output:{out_port}"
            switch.dpctl('add-flow', flow)

    info("*** Done building X–Y routes\n")

def run_mesh_xy(k):
    info(f"*** Creating {k}x{k} mesh topology\n")
    topo = MeshTopology(r=k)
    net = Mininet(topo=topo, switch=OVSSwitch, controller=None, link=TCLink, autoSetMacs=True, autoStaticArp=False)
    net.start()

    info("*** Network started\n")
    switch_coord_map, host_coord_map = build_coord_maps(net)
    ports = build_ports_map(net, switch_coord_map, host_coord_map)
    build_arp(host_coord_map)
    build_xy_routes(ports, switch_coord_map, host_coord_map)

    info("*** Testing connectivity with pingAll()\n")
    net.pingAll()

    info("*** Entering Mininet CLI\n")
    CLI(net)
    net.stop()

if __name__ == "__main__":
    setLogLevel('info')
    if len(sys.argv) > 1:
        k = int(sys.argv[1])
    else:
        k = 3
    run_mesh_xy(k)