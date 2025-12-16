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

def _dq_next_coord(current, dest, d):
    group, i = current
    dest_group, di = dest
    if current == dest:
        return None
    
    if group != dest_group: #phase 1 of algo
        bit_difference = group ^ dest_group
        for bit in range(d - 1):
            if bit_difference & (1 << bit):
                bit_mask = 1 << bit
                if bit_difference & bit_mask:
                    next_group = group ^ bit_mask
                    return (next_group, i)
    
    if i != di: #phase 2 of algo
        j = _DIAMOND_NEXT_HOP[(i, di)]
        return (group, j)
    return None

def build_dq_routes(switch_coord_map, host_coord_map, d=None):
    info("*** Building DQ one-to-one routing flows (Algorithm 1)\n")
    ports, d = build_dq_ports_map(switch_coord_map, host_coord_map, d)
    flows_by_switch = {sw: [] for sw in switch_coord_map.values()}

    for dest_coord, host_dest in host_coord_map.items():
        dest_ip = host_dest.IP()

        for coord, switch in switch_coord_map.items():
            if coord == dest_coord:
                out_port = ports[coord]["host"]
            else:
                next_coord = _dq_next_coord(coord, dest_coord, d)
                neighbors = ports[coord]["neighbors"]
                out_port = neighbors[next_coord]

            flow = f"priority=100,ip,nw_dst={dest_ip},actions=output:{out_port}"
            flows_by_switch[switch].append(flow)

    for sw, flows in flows_by_switch.items():
        add_flows_bulk(sw, flows)

    info("*** Done building DQ routes\n")
