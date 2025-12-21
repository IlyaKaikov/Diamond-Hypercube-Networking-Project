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
    info(f"**** Building topology '{config.topo}' ****\n")
    net = Mininet(topo=topo, switch=OVSSwitch, controller=None, autoSetMacs=True, autoStaticArp=True,)
    info("**** Starting network ****\n")
    net.start()
    return net

def install_static_routes(net, config: TopologyConfig):
    from mininet.log import info
    from routing.utils import build_coord_maps, build_ports_map
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

    return switch_coord_map, host_coord_map

def choose_default_probe_pair(net, config: Optional[TopologyConfig] = None):
    hosts = list(net.hosts)
    if len(hosts) < 2:
        raise ValueError("Network must have at least two hosts to choose a probe pair")

    try:
        from routing.utils import build_coord_maps
        _, host_coord_map = build_coord_maps(net)
    except Exception:
        host_coord_map = None

    topo = config.topo if config is not None else None
    if not host_coord_map:
        return hosts[0], hosts[-1]

    if topo in ("mesh", "torus2d"):
        coords = list(host_coord_map.keys())
        max_i = max(i for i, _ in coords)
        max_j = max(j for _, j in coords)
        r = max(max_i, max_j) + 1

        src_coord = (0, 0)
        dst_coord = (r - 1, r - 1) if topo == "mesh" else (r // 2, r // 2)

        if src_coord in host_coord_map and dst_coord in host_coord_map:
            return host_coord_map[src_coord], host_coord_map[dst_coord]

    if topo == "dq":
        coords = list(host_coord_map.keys())
        groups = {g for (g, _) in coords}
        num_groups = len(groups)
        d = int(config.d) if (config is not None and config.d is not None) else num_groups.bit_length()
        max_group = (1 << (d - 1)) - 1

        src_coord = (0, 1)
        dst_coord = (max_group, 6)
        if src_coord in host_coord_map and dst_coord in host_coord_map:
            return host_coord_map[src_coord], host_coord_map[dst_coord]

    return hosts[0], hosts[-1]
