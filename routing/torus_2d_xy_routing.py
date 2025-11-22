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

from topology.torus_2d_topology import Torus2DTopology
from routing.utils import build_coord_maps, build_ports_map, build_arp
from routing.xy_routing import build_xy_routes

def run_torus_2d_xy(k):
    info(f"*** Creating {k}x{k} 2d torus topology\n")
    topo = Torus2DTopology(r=k)
    net = Mininet(topo=topo, switch=OVSSwitch, controller=None, link=TCLink, autoSetMacs=True, autoStaticArp=False)
    net.start()

    info("*** Network started\n")
    switch_coord_map, host_coord_map = build_coord_maps(net)
    ports = build_ports_map(switch_coord_map, host_coord_map, is_torus=True)
    build_arp(host_coord_map)
    build_xy_routes(ports, switch_coord_map, host_coord_map, is_torus=True)

    info("*** Testing connectivity with pingAll()\n")
    net.pingAll()

    info("*** Entering Mininet CLI\n")
    CLI(net)
    net.stop()

if __name__ == "__main__":
    setLogLevel('info')
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    run_torus_2d_xy(k)