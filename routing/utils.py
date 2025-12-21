import re
import tempfile
import os

SWITCH_REGEX = re.compile(r"s(\d+)x(\d+)$")
HOST_REGEX = re.compile(r"h(\d+)x(\d+)$")

def coord_from_name(name, is_switch = True):
    regex = SWITCH_REGEX if is_switch else HOST_REGEX
    res = regex.match(name)
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
    interface = links[0][0]
    return switch.ports[interface]

def _grid_size(coords):
    max_i = max(i for i, _ in coords)
    return max_i + 1

def build_ports_map(switch_coord_map, host_coord_map, is_torus = False):
    ports = {}
    coords = sorted(switch_coord_map.keys())
    r = _grid_size(coords) if is_torus else None

    for (i, j) in coords:
        switch = switch_coord_map[(i, j)]
        ports[(i, j)] = {}
        host = host_coord_map[(i, j)]
        ports[(i, j)]["host"] = port_to_neighbor(switch, host)

        if is_torus:
            assert r is not None
            up_coord = ((i - 1) % r, j)
            down_coord = ((i + 1) % r, j)
            left_coord = (i, (j - 1) % r)
            right_coord = (i, (j + 1) % r)
        
        else:
            up_coord = (i - 1, j)
            down_coord = (i + 1, j)
            left_coord = (i, j - 1)
            right_coord = (i, j + 1)

        neighbors = {"up": up_coord, "down": down_coord, "left": left_coord, "right": right_coord}

        for direction, coords in neighbors.items():
            if coords in switch_coord_map:
                neighbor_switch = switch_coord_map[coords]
                ports[(i, j)][direction] = port_to_neighbor(switch, neighbor_switch)

            else:
                ports[(i, j)][direction] = None

    return ports

def add_flows_bulk(switch, flows):
    if not flows:
        return

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("\n".join(flows))
        f.write("\n")
        path = f.name
    try:
        switch.cmd(f"ovs-ofctl add-flows {switch.name} {path}")
    finally:
        os.unlink(path)
        