import random
from typing import Optional

def _find_host_by_name(hosts, name: str):
    for h in hosts:
        if getattr(h, "name", None) == name:
            return h
    return None

def choose_destination(hosts, seed: Optional[int] = None, dst_host: Optional[str] = None):
    if not hosts:
        raise ValueError("hosts list is empty")

    if dst_host:
        dst = _find_host_by_name(hosts, dst_host)
        if dst is None:
            raise ValueError(f"Unknown destination host '{dst_host}'.")
        return dst

    rand = random.Random(seed)
    return rand.choice(hosts)

def generate_incast_pairs_n(hosts, n, *, dst_seed: Optional[int] = None, src_seed: Optional[int] = None, allow_dst_as_source = False, dst_host: Optional[str] = None,):
    if not hosts:
        return [], None
    if n <= 0:
        return [], None

    dst = choose_destination(hosts, seed=dst_seed, dst_host=dst_host)

    if allow_dst_as_source:
        eligible_sources = list(hosts)
    else:
        eligible_sources = [h for h in hosts if h is not dst]

    if not eligible_sources:
        return [], dst

    rand_src = random.Random(src_seed if src_seed is not None else dst_seed)
    pairs = []
    for _ in range(n):
        src = rand_src.choice(eligible_sources)
        pairs.append((src, dst))

    return pairs, dst
