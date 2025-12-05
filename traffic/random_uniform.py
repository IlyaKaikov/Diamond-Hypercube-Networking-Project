import random
from typing import List, Tuple, Any, Optional

def generate_uniform_pairs(hosts, seed: Optional[int] = None, allow_self = False):
    if not hosts:
        return []

    rng = random.Random(seed)
    pairs = []

    for src in hosts:
        if allow_self:
            dst = rng.choice(hosts)

        else:
            choices = [h for h in hosts if h is not src]
            if not choices:
                continue
            dst = rng.choice(choices)

        pairs.append((src, dst))

    return pairs

def generate_uniform_pairs_k(hosts, k, seed: Optional[int] = None, allow_self = False,):
    if not hosts or k <= 0:
        return []

    rng = random.Random(seed)
    pairs = []

    for _ in range(k):
        for src in hosts:
            if allow_self:
                dst = rng.choice(hosts)
            else:
                choices = [h for h in hosts if h is not src]
                if not choices:
                    continue
                dst = rng.choice(choices)
            pairs.append((src, dst))

    return pairs