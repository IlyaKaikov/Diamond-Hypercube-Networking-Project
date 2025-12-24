import random
from typing import Optional

def choose_random_destination(hosts, seed: Optional[int] = None):
    if not hosts:
        raise ValueError("hosts list is empty")
    rand = random.Random(seed)
    return rand.choice(hosts)

def generate_incast_pairs_n(hosts, n, *, dst_seed: Optional[int] = None, src_seed: Optional[int] = None, allow_dst_as_source = False,):
    if not hosts:
        return [], None
    if n <= 0:
        return [], None

    dst = choose_random_destination(hosts, seed=dst_seed)

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
