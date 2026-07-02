"""
Data912Provider — API pública y gratuita (data912.com), verificada contra la
OpenAPI spec oficial. Los paneles /live/* de acciones/bonos/cedears/adrs usan
el schema Panel: symbol, c (último), px_bid, px_ask, pct_change, v (volumen).
Refresco declarado: ~20 s. No es real-time garantizado; para cliente final, BYMA.

MEP/CCL tienen schema propio (mark = valor medio). Se toma un valor
representativo ponderado por volumen (fallback: mediana).
"""
from __future__ import annotations
import statistics
import httpx
from .base import FeedProvider, Quote

BASE = "https://data912.com"

# cada mercado se arma barriendo uno o más paneles
MERCADO_PANELS = {
    "arg_fi":      ["/live/arg_notes", "/live/arg_bonds", "/live/arg_corp"],
    "arg_eq":      ["/live/arg_stocks"],
    "arg_cedears": ["/live/arg_cedears"],
    "usa_adrs":    ["/live/usa_adrs"],
    "usa_stocks":  ["/live/usa_stocks"],
}


def _f(v):
    return float(v) if isinstance(v, (int, float)) else None


class Data912Provider(FeedProvider):
    name = "data912"

    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout

    def _get(self, client, path):
        try:
            r = client.get(BASE + path)
            r.raise_for_status()
            d = r.json()
            return d if isinstance(d, list) else []
        except Exception:
            return []

    def fetch(self) -> dict[str, dict[str, Quote]]:
        out: dict[str, dict[str, Quote]] = {m: {} for m in MERCADO_PANELS}
        with httpx.Client(timeout=self.timeout,
                          headers={"accept": "application/json"}) as c:
            for mercado, panels in MERCADO_PANELS.items():
                for p in panels:
                    for row in self._get(c, p):
                        sym = row.get("symbol")
                        if not sym:
                            continue
                        out[mercado][sym] = Quote(
                            symbol=sym,
                            last=_f(row.get("c")),
                            bid=_f(row.get("px_bid")),
                            ask=_f(row.get("px_ask")),
                            var_pct=_f(row.get("pct_change")),
                            volume=_f(row.get("v")),
                            ts=self._now(),
                        )
        return out

    def fetch_fx(self) -> dict:
        with httpx.Client(timeout=self.timeout,
                          headers={"accept": "application/json"}) as c:
            mep_rows = self._get(c, "/live/mep")
            ccl_rows = self._get(c, "/live/ccl")
        return {"mep": _weighted(mep_rows, "mark", "v_usd"),
                "ccl": _weighted(ccl_rows, "CCL_mark", "ars_volume")}


def _weighted(rows, val_key, w_key):
    """Valor representativo: promedio ponderado por volumen; fallback mediana."""
    vals, num, den = [], 0.0, 0.0
    for r in rows:
        v = r.get(val_key)
        if not isinstance(v, (int, float)) or v <= 0:
            continue
        vals.append(float(v))
        w = r.get(w_key)
        w = float(w) if isinstance(w, (int, float)) and w > 0 else 0.0
        num += v * w
        den += w
    if den > 0:
        return round(num / den, 2)
    if vals:
        return round(statistics.median(vals), 2)
    return None
