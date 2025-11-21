#!/usr/bin/env python3

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

def compute_ports(net, sw_by_coord, host_by_coord):
    ports = {}
    coords = sorted(sw_by_coord.keys())

    for (i, j) in coords:
        sw = sw_by_coord[(i, j)]
        ports[(i, j)] = {}

        # To local host
        h = host_by_coord[(i, j)]
        ports[(i, j)]['host'] = port_to_neighbor(sw, h)

        # Potential neighbors
        neighbors = {
            'up':    (i - 1, j),
            'down':  (i + 1, j),
            'left':  (i, j - 1),
            'right': (i, j + 1)
        }

        for direction, coord in neighbors.items():
            if coord in sw_by_coord:
                neigh_sw = sw_by_coord[coord]
                ports[(i, j)][direction] = port_to_neighbor(sw, neigh_sw)
            else:
                ports[(i, j)][direction] = None

    return ports

def install_static_arp(host_by_coord):
    coords = list(host_by_coord.keys())
    for src_coord in coords:
        h1 = host_by_coord[src_coord]
        for dst_coord in coords:
            if src_coord == dst_coord:
                continue
            h2 = host_by_coord[dst_coord]
            h1.setARP(ip=h2.IP(), mac=h2.MAC())

def install_xy_routes(ports, sw_by_coord, host_by_coord):
    info("*** Installing X–Y routing flows\n")
    for (dx, dy), h_dst in host_by_coord.items():
        dst_ip = h_dst.IP()

        for (x, y), sw in sw_by_coord.items():

            if (x, y) == (dx, dy):
                out_port = ports[(x, y)]['host']
            else:
                if x != dx:
                    direction = 'down' if dx > x else 'up'
                else:
                    direction = 'right' if dy > y else 'left'

                out_port = ports[(x, y)][direction]

                if out_port is None:
                    raise Exception(
                        f"No port for direction {direction} "
                        f"at switch ({x},{y}) when routing to ({dx},{dy})"
                    )
            flow = f"priority=100,ip,nw_dst={dst_ip},actions=output:{out_port}"
            sw.dpctl('add-flow', flow)

    info("*** Done installing X–Y routes\n")

def run_mesh_xy(k):
    info(f"*** Creating {k}x{k} mesh topology\n")
    topo = MeshTopology(r=k)
    net = Mininet(topo=topo, switch=OVSSwitch, controller=None, link=TCLink, autoSetMacs=True, autoStaticArp=False)
    net.start()
    info("*** Network started\n")
    # Build coordinate to node maps
    sw_by_coord, host_by_coord = build_coord_maps(net)
    # Compute per-direction ports
    ports = compute_ports(net, sw_by_coord, host_by_coord)
    # Pre-populate ARP tables
    install_static_arp(host_by_coord)
    # Install static X–Y routing flows
    install_xy_routes(ports, sw_by_coord, host_by_coord)
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