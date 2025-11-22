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

from topology.dq_topology import DQTopology
from routing.utils import build_coord_maps, build_arp
from routing.dq_routing import build_dq_routes

def run_dq(d):
    info(f"*** Creating DQ topology with dimension d={d}\n")
    topo = DQTopology(d=d)
    net = Mininet(topo=topo, switch=OVSSwitch, controller=None, link=TCLink, autoSetMacs=True, autoStaticArp=False)
    net.start()

    info("*** Network started\n")
    switch_coord_map, host_coord_map = build_coord_maps(net)
    build_arp(host_coord_map)
    build_dq_routes(switch_coord_map, host_coord_map)

    info("*** Testing connectivity with pingAll()\n")
    net.pingAll()

    info("*** Entering Mininet CLI\n")
    CLI(net)
    net.stop()

if __name__ == "__main__":
    setLogLevel('info')
    d = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    run_dq(d)