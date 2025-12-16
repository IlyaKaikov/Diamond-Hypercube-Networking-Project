from collections import deque
from mininet.log import info

from .utils import (port_to_neighbor, add_flows_bulk,)

DIAMOND_NEIGHBORS = {
    0: [1, 2, 4],
    1: [0, 3, 5],
    2: [0, 3, 6],
    3: [1, 2],
    4: [0, 5, 6],
    5: [1, 4],
    6: [2, 4],
}

def _dimension_size(switch_coord_map):
    groups = {group for (group, _) in switch_coord_map.keys()}
    num_groups = len(groups)

    if num_groups == 1:
        return 1
    
    return num_groups.bit_length()

def _diamond_next_hop():
    nodes = range(7)
    next_hop = {}

    for src in nodes:
        parent = {src: None}
        q = deque([src])

        while q: # doing BFS
            current = q.popleft()

            for neighbor in DIAMOND_NEIGHBORS[current]:
                if neighbor not in parent:
                    parent[neighbor] = current
                    q.append(neighbor)
    
        for dest in nodes:
            if dest == src:
                continue
            
            current = dest
            while parent[current] != src:
                current = parent[current]
            next_hop[(src, dest)] = current
    
    return next_hop

_DIAMOND_NEXT_HOP = _diamond_next_hop() #this func needs to be called only once to get all next hops

def build_dq_ports_map(switch_coord_map, host_coord_map, d = None):
    if d == None:
        d = _dimension_size(switch_coord_map)
    ports = {} # ports[(group, i)]["host"] = port to host, ports[(group, i)]["neighbors"][(neighbor_group, j)] = port to neighbor switch

    for (group, i), switch in switch_coord_map.items():
        entry_dict = {}
        host = host_coord_map[(group, i)]
        entry_dict["host"] = port_to_neighbor(switch, host)

        neighbors = {}
        for j in DIAMOND_NEIGHBORS[i]:
            neighbor_switch = switch_coord_map[(group, j)]
            neighbors[(group, j)] = port_to_neighbor(switch, neighbor_switch)

        if d > 1:   
            group_bits = d - 1
            for bit in range(group_bits):
                neighbor_group = group ^ (1 << bit)
                neighbor_switch = switch_coord_map[(neighbor_group, i)]
                neighbors[(neighbor_group, i)] = port_to_neighbor(switch, neighbor_switch)
        
        entry_dict["neighbors"] = neighbors
        ports[(group, i)] = entry_dict
    
    return ports, d

def build_dq_routes(switch_coord_map, host_coord_map, d=None):
    info("*** Building DQ routing flows (prefix aggregated)\n")
    ports, d = build_dq_ports_map(switch_coord_map, host_coord_map, d)
    m = d - 1
    if m > 16:
        raise ValueError("This IPv4 encoding supports at most d<=17 (group bits <=16)")

    shift = 16 - m if m > 0 else 0

    def group_tag(g):
        return (g << shift) & 0xFFFF

    def tag_bytes(tag):
        return (tag >> 8) & 0xFF, tag & 0xFF

    for (g, p_src), sw in switch_coord_map.items():
        flows = []
        tag_g = group_tag(g)

        # Phase 1
        for b in range(m):
            bit_to_flip = (m - 1 - b)
            neighbor_group = g ^ (1 << bit_to_flip)
            out_port = ports[(g, p_src)]["neighbors"][(neighbor_group, p_src)]
            prefix_len = 8 + (b + 1)
            prefix_tag = tag_g ^ (1 << (15 - b))
            gh, gl = tag_bytes(prefix_tag)
            flows.append(f"priority=200,ip,nw_dst=10.{gh}.{gl}.0/{prefix_len},actions=output:{out_port}")

        # Phase 2
        gh, gl = tag_bytes(tag_g)
        for p_dst in range(7):
            if p_dst == p_src:
                out_port = ports[(g, p_src)]["host"]
            else:
                next_p = _DIAMOND_NEXT_HOP[(p_src, p_dst)]
                out_port = ports[(g, p_src)]["neighbors"][(g, next_p)]

            dst_ip = f"10.{gh}.{gl}.{p_dst+1}"
            flows.append(f"priority=100,ip,nw_dst={dst_ip}/32,actions=output:{out_port}")

        add_flows_bulk(sw, flows)

    info("*** Done building DQ routes (prefix aggregated)\n")
