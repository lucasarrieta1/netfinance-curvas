"""
Interfaz común de proveedores de precios (patrón adaptador).

Para agregar un proveedor nuevo (BYMA, IOL, PPI, Cocos, ...) sólo hay que
crear una subclase de FeedProvider e implementar `fetch()`.  El resto del
sistema (cálculo, endpoints, front) queda intacto: se cambia UNA línea en
config.py.

`fetch()` devuelve un dict:  { feed_symbol: Quote }
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import datetime as _dt


@dataclass
class Quote:
    symbol: str
    last: Optional[float] = None          # último precio operado
    bid: Optional[float] = None
    ask: Optional[float] = None
    prev_close: Optional[float] = None    # cierre anterior
    var_pct: Optional[float] = None       # variación % del día
    volume: Optional[float] = None
    ts: Optional[str] = None              # hora del dato

    @property
    def price(self) -> Optional[float]:
        """Precio de referencia para valuar: last, o mid, o bid/ask."""
        if self.last:
            return self.last
        if self.bid and self.ask:
            return (self.bid + self.ask) / 2
        return self.bid or self.ask


class FeedProvider:
    name = "base"

    def fetch(self, symbols: list[str]) -> dict[str, Quote]:
        raise NotImplementedError

    # utilidad para subclases
    @staticmethod
    def _now() -> str:
        return _dt.datetime.now().strftime("%H:%M:%S")
