from mininet.log import info
from .utils import add_flows_bulk

def _grid_size(coords):
    max_i = max(i for i, _ in coords)
    max_j = max(j for _, j in coords)
    if max_i != max_j:
        raise ValueError("Grid is not square")

    return max_i + 1

def build_xy_routes(ports, switch_coord_map, host_coord_map, is_torus=False):
    info("*** Building X–Y routing flows (prefix aggregated)\n")
    coords = sorted(switch_coord_map.keys())
    r = _grid_size(coords)

    def torus_dir_1d(cur, dst):
        dist_pos = (dst - cur) % r
        dist_neg = (cur - dst) % r
        return ("pos" if dist_pos <= dist_neg else "neg")

    for (x, y), sw in switch_coord_map.items():
        flows = []
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

            flows.append(f"priority=200,ip,nw_dst=10.{dx}.0.0/16,actions=output:{out_port}")

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

            flows.append(f"priority=100,ip,nw_dst=10.{x}.{dy}.0/24,actions=output:{out_port}")

        add_flows_bulk(sw, flows)

    info("*** Done building X–Y routes (prefix aggregated)\n")
