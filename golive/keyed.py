"""Keyed randomness: every draw is a function of (seed, what is drawn, which entity), so every design meets the same
customers, the same slow IT departments and the same reviewers' mistakes."""

from __future__ import annotations

import hashlib
import random


class Keyed:
    def __init__(self, seed: int) -> None:
        self.seed = seed

    def rng(self, tag: str, *ids: int) -> random.Random:
        h = hashlib.blake2b(f"{self.seed}|{tag}|{'|'.join(map(str, ids))}".encode(), digest_size=8).digest()
        r = random.Random(int.from_bytes(h, "big"))
        return r

    def u(self, tag: str, *ids: int) -> float:
        return self.rng(tag, *ids).random()


def poisson(r: random.Random, mean: float) -> int:
    import math

    lim, k, p = math.exp(-mean), 0, 1.0
    while True:
        p *= r.random()
        if p <= lim:
            return k
        k += 1
