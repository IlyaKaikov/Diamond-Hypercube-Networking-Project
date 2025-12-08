from dataclasses import dataclass
from typing import Optional

@dataclass
class TopologyConfig:
    topo: str
    r: Optional[int] = None
    d: Optional[int] = None

    def validate(self):
        if self.topo not in ("mesh", "torus2d", "dq"):
            raise ValueError(f"Unsupported topology '{self.topo}'")

        if self.topo in ("mesh", "torus2d") and self.r is None:
            raise ValueError(f"Topology '{self.topo}' requires parameter r")

        if self.topo == "dq" and self.d is None:
            raise ValueError("Topology 'dq' requires parameter d")

def build_topology(config: TopologyConfig):
    from importlib import import_module

    config.validate()

    if config.topo == "mesh":
        module = import_module("topology.mesh_topology")
        topo_cls = getattr(module, "MeshTopology")
        return topo_cls(r=int(config.r))

    if config.topo == "torus2d":
        module = import_module("topology.torus_2d_topology")
        topo_cls = getattr(module, "Torus2DTopology")
        return topo_cls(r=int(config.r))

    if config.topo == "dq":
        module = import_module("topology.dq_topology")
        topo_cls = getattr(module, "DQTopology")
        return topo_cls(d=int(config.d))

    raise ValueError(f"Unsupported topology '{config.topo}'")

def create_and_start_network(config: TopologyConfig):
    from mininet.net import Mininet
    from mininet.node import OVSSwitch
    from mininet.log import info

    topo = build_topology(config)
    info(f"*** Building topology '{config.topo}'\n")
    net = Mininet(topo=topo, switch=OVSSwitch, controller=None, autoSetMacs=True, autoStaticArp=True,)
    info("*** Starting network\n")
    net.start()
    return net

def install_static_routes(net, config: TopologyConfig):
    from mininet.log import info
    from routing.utils import build_coord_maps, build_ports_map, build_arp
    from routing.xy_routing import build_xy_routes
    from routing.dq_routing import build_dq_routes

    config.validate()
    switch_coord_map, host_coord_map = build_coord_maps(net)
    if config.topo in ("mesh", "torus2d"):
        is_torus = config.topo == "torus2d"
        ports = build_ports_map(switch_coord_map=switch_coord_map, host_coord_map=host_coord_map, is_torus=is_torus,)
        build_xy_routes(ports=ports, switch_coord_map=switch_coord_map, host_coord_map=host_coord_map, is_torus=is_torus,)

    elif config.topo == "dq":
        build_dq_routes(switch_coord_map=switch_coord_map, host_coord_map=host_coord_map, d=config.d,)

    else:
        raise ValueError(f"Unsupported topology '{config.topo}' for routing")

    build_arp(host_coord_map)
    info("*** Static routes and ARP entries installed\n")
    return switch_coord_map, host_coord_map

def choose_default_probe_pair(net):
    hosts = list(net.hosts)
    if len(hosts) < 2:
        raise ValueError("Network must have at least two hosts to choose a probe pair")

    src = hosts[0]
    dst = hosts[-1]
    return src, dst
