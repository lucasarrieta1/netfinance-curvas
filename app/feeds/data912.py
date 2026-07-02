"""
Data912Provider — API pública y gratuita (data912.com).

Verificado contra la OpenAPI spec oficial (ferminrp/agent-skills).
Los paneles /live/* devuelven el schema `Panel`:
    symbol, q_bid, px_bid, px_ask, q_ask, v, q_op, c, pct_change
donde  c = último precio,  px_bid/px_ask = puntas,  pct_change = variación %,
v = volumen.

OJO: data912 declara el dato como educativo y NO en tiempo real (caché ~2 h,
~120 req/min). Sirve para prototipar la curva, NO para precios en vivo a cliente.
Sin autenticación.
"""
from __future__ import annotations
import httpx
from .base import FeedProvider, Quote

BASE = "https://data912.com"
# paneles a barrer (se combinan en un índice symbol->quote):
#   arg_notes = letras (LECAP) · arg_bonds = bonos (incluye variantes D/C) · arg_corp = ONs
# Si las variantes dólar (AL30D, GD30D...) no aparecieran en arg_bonds, sumá
# el panel correspondiente acá; el resto del sistema no cambia.
PANELS = ["/live/arg_notes", "/live/arg_bonds", "/live/arg_corp"]


def _f(v):
    return float(v) if isinstance(v, (int, float)) else None


class Data912Provider(FeedProvider):
    name = "data912"

    def __init__(self, timeout: float = 8.0, panels: list[str] | None = None):
        self.timeout = timeout
        self.panels = panels or PANELS

    def _rows(self) -> list[dict]:
        rows: list[dict] = []
        with httpx.Client(timeout=self.timeout,
                          headers={"accept": "application/json"}) as c:
            for p in self.panels:
                try:
                    r = c.get(BASE + p)
                    r.raise_for_status()
                    data = r.json()
                    if isinstance(data, list):
                        rows.extend(data)
                except Exception:
                    continue  # un panel caído no tumba el resto
        return rows

    def fetch(self, symbols: list[str]) -> dict[str, Quote]:
        want = set(symbols)
        out: dict[str, Quote] = {}
        for row in self._rows():
            sym = row.get("symbol")
            if not sym or sym not in want:
                continue
            out[sym] = Quote(
                symbol=sym,
                last=_f(row.get("c")),
                bid=_f(row.get("px_bid")),
                ask=_f(row.get("px_ask")),
                var_pct=_f(row.get("pct_change")),
                volume=_f(row.get("v")),
                ts=self._now(),
            )
        return out
