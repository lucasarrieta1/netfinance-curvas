"""
Interfaz común de proveedores de precios (patrón adaptador).

fetch() devuelve un snapshot ANIDADO por mercado, para evitar colisiones de
tickers entre mercados (p.ej. GGAL acción local vs GGAL ADR, AAPL CEDEAR vs
AAPL acción USA):

    { mercado: { symbol: Quote } }

Mercados:
    arg_fi       renta fija ARS/USD (LECAP/BONCAP/HD/CER)  [notes+bonds+corp]
    arg_eq       acciones argentinas (panel líder)          [arg_stocks]
    arg_cedears  CEDEARs                                     [arg_cedears]
    usa_adrs     ADRs argentinos en USA                      [usa_adrs]
    usa_stocks   acciones USA                                [usa_stocks]

fetch_fx() devuelve el dólar financiero: { "mep": float|None, "ccl": float|None }
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import datetime as _dt

MERCADOS = ["arg_fi", "arg_eq", "arg_cedears", "usa_adrs", "usa_stocks"]


@dataclass
class Quote:
    symbol: str
    last: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    var_pct: Optional[float] = None
    volume: Optional[float] = None
    ts: Optional[str] = None

    @property
    def price(self) -> Optional[float]:
        if self.last:
            return self.last
        if self.bid and self.ask:
            return (self.bid + self.ask) / 2
        return self.bid or self.ask


class FeedProvider:
    name = "base"

    def fetch(self) -> dict[str, dict[str, Quote]]:
        """Devuelve {mercado: {symbol: Quote}}."""
        raise NotImplementedError

    def fetch_fx(self) -> dict[str, Optional[float]]:
        """Dólar MEP y CCL. Por defecto no disponible."""
        return {"mep": None, "ccl": None}

    @staticmethod
    def _now() -> str:
        return _dt.datetime.now().strftime("%H:%M:%S")
