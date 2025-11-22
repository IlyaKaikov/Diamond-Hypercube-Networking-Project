from mininet.log import info

def _grid_size(coords):
    max_i = max(i for i, _ in coords)
    max_j = max(j for _, j in coords)
    if max_i != max_j:
        raise ValueError("Grid is not square")

    return max_i + 1

def _direction_mesh(x, y, dx, dy):
    if x != dx:
        return 'down' if dx > x else 'up'
    elif y != dy:
        return 'right' if dy > y else 'left'
    else:
        return None

def _direction_2d_torus(x, y, dx, dy, r):
    if (x, y) == (dx, dy):
        return None
    
    if x != dx:
        distance_down = (dx - x) % r
        distance_up = (x - dx) % r
        return 'down' if distance_down <= distance_up else 'up'
    
    if y != dy:
        distance_right = (dy - y) % r
        distance_left = (y - dy) % r
        return 'right' if distance_right <= distance_left else 'left'

    return None

def build_xy_routes(ports, switch_coord_map, host_coord_map, is_torus = False):
    info("*** Building X–Y routing flows\n")
    r = _grid_size(switch_coord_map.keys()) if is_torus else None

    for (dx, dy), h_dest in host_coord_map.items():
        dest_ip = h_dest.IP()

        for (x, y), switch in switch_coord_map.items():
            if (x, y) == (dx, dy):
                out_port = ports[(x, y)]['host']

            else:
                if is_torus:
                    assert r is not None
                    direction = _direction_2d_torus(x, y, dx, dy, r)
                else:
                    direction = _direction_mesh(x, y, dx, dy)
                
                if direction is None:
                    raise Exception(f"Can't find direction from ({x},{y}) to ({dx},{dy})")

                out_port = ports[(x, y)][direction]

                if out_port is None:
                    raise Exception(f"Closed port for direction {direction} from switch ({x},{y}) to ({dx},{dy})")

            flow = f"priority=100,ip,nw_dst={dest_ip},actions=output:{out_port}"
            switch.dpctl('add-flow', flow)

    info("*** Done building X–Y routes\n")