"""
MockProvider — sin red. Usa el registro de instrumentos (mercado, símbolo,
precio de referencia) para devolver un snapshot anidado con ruido, y valores
fijos de MEP/CCL, para que toda la web renderice offline.
"""
from __future__ import annotations
import random
from .base import FeedProvider, Quote, MERCADOS
from ..instruments import REGISTRY


class MockProvider(FeedProvider):
    name = "mock"

    def __init__(self, jitter: float = 0.004, seed: int | None = None):
        self.jitter = jitter
        self._rng = random.Random(seed)

    def fetch(self) -> dict[str, dict[str, Quote]]:
        out: dict[str, dict[str, Quote]] = {m: {} for m in MERCADOS}
        for it in REGISTRY:
            base = it["px_ref"]
            if base is None:
                continue
            last = round(base * (1 + self._rng.uniform(-self.jitter, self.jitter)), 4)
            var = (last / base - 1) * 100
            out.setdefault(it["market"], {})[it["feed_symbol"]] = Quote(
                symbol=it["feed_symbol"], last=last,
                var_pct=round(var, 3), ts=self._now())
        return out

    def fetch_fx(self) -> dict:
        j = lambda base: round(base * (1 + self._rng.uniform(-0.003, 0.003)), 2)
        return {"mep": j(1305.0), "ccl": j(1355.0)}
