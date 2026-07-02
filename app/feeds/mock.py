"""
MockProvider — no toca la red.

Devuelve los últimos precios conocidos (del Excel) con un pequeño ruido
aleatorio, para que la web renderice y se vea "viva" sin feed real.
Ideal para desarrollar el front o hacer una demo offline.
"""
from __future__ import annotations
import random
from .base import FeedProvider, Quote
from ..instruments import PX_REF


class MockProvider(FeedProvider):
    name = "mock"

    def __init__(self, jitter: float = 0.002, seed: int | None = None):
        self.jitter = jitter
        self._rng = random.Random(seed)

    def fetch(self, symbols: list[str]) -> dict[str, Quote]:
        out: dict[str, Quote] = {}
        for s in symbols:
            base = PX_REF.get(s)
            if base is None:
                continue
            last = round(base * (1 + self._rng.uniform(-self.jitter, self.jitter)), 4)
            var = (last / base - 1) * 100
            out[s] = Quote(symbol=s, last=last, prev_close=base,
                           var_pct=round(var, 3), ts=self._now())
        return out
