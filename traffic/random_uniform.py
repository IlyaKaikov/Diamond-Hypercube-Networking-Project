import random
from typing import Optional

def generate_uniform_pairs(hosts, seed: Optional[int] = None, allow_self = False):
    if not hosts:
        return []
    rand = random.Random(seed)
    pairs = []
    for src in hosts:
        if allow_self:
            dest = rand.choice(hosts)
        else:
            choices = [h for h in hosts if h is not src]
            if not choices:
                continue
            dest = rand.choice(choices)
        pairs.append((src, dest))

    return pairs

def generate_uniform_pairs_k(hosts, k, seed: Optional[int] = None, allow_self = False,):
    if not hosts or k <= 0:
        return []
    rand = random.Random(seed)
    pairs = []
    for _ in range(k):
        for src in hosts:
            if allow_self:
                dest = rand.choice(hosts)
            else:
                choices = [h for h in hosts if h is not src]
                if not choices:
                    continue
                dest = rand.choice(choices)
            pairs.append((src, dest))

    return pairs