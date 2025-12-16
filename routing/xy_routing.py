from mininet.log import info
from .utils import add_flows_bulk

def _grid_size(coords):
    max_i = max(i for i, _ in coords)
    max_j = max(j for _, j in coords)
    if max_i != max_j:
        raise ValueError("Grid is not square")

    return max_i + 1

def _direction_mesh(x, y, dx, dy):
    if x != dx:
        return "down" if dx > x else "up"
    elif y != dy:
        return "right" if dy > y else "left"
    else:
        return None

def _direction_2d_torus(x, y, dx, dy, r):
    if (x, y) == (dx, dy):
        return None
    
    if x != dx:
        distance_down = (dx - x) % r
        distance_up = (x - dx) % r
        return "down" if distance_down <= distance_up else "up"
    
    if y != dy:
        distance_right = (dy - y) % r
        distance_left = (y - dy) % r
        return "right" if distance_right <= distance_left else "left"

    return None

def build_xy_routes(ports, switch_coord_map, host_coord_map, is_torus=False):
    info("*** Building X–Y routing flows (prefix aggregated)\n")
    coords = sorted(switch_coord_map.keys())
    r = _grid_size(coords)

    def torus_dir_1d(cur, dst):
        dist_pos = (dst - cur) % r
        dist_neg = (cur - dst) % r
        return ("pos" if dist_pos <= dist_neg else "neg")

    for (x, y), sw in switch_coord_map.items():
        for dx in range(r):
            if dx == x:
                continue

            if not is_torus:
                direction = "down" if dx > x else "up"
            else:
                direction = "down" if torus_dir_1d(x, dx) == "pos" else "up"

            out_port = ports[(x, y)][direction]
            if out_port is None:
                raise Exception(f"Missing port {direction} at switch ({x},{y})")

            flow = f"priority=200,ip,nw_dst=10.{dx}.0.0/16,actions=output:{out_port}"
            sw.dpctl("add-flow", flow)

        for dy in range(r):
            if dy == y:
                out_port = ports[(x, y)]["host"]
            else:
                if not is_torus:
                    direction = "right" if dy > y else "left"
                else:
                    direction = "right" if torus_dir_1d(y, dy) == "pos" else "left"

                out_port = ports[(x, y)][direction]
                if out_port is None:
                    raise Exception(f"Missing port {direction} at switch ({x},{y})")

            flow = f"priority=100,ip,nw_dst=10.{x}.{dy}.0/24,actions=output:{out_port}"
            sw.dpctl("add-flow", flow)

    info("*** Done building X–Y routes (prefix aggregated)\n")
