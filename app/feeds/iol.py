"""
IOLProvider — feed del broker IOL (invertironline), tiempo real con tu cuenta.

Alternativa de producción si operás vía IOL: la API devuelve cotizaciones en
tiempo real de bonos, letras, acciones, etc. (réplica de su sitio, JSON).
Auth por usuario/clave -> bearer token (OAuth2 password grant).

Config (.env):  IOL_USER, IOL_PASSWORD
Docs: https://api.invertironline.com  (v2)
"""
from __future__ import annotations
import os
import time
import httpx
from .base import FeedProvider, Quote

TOKEN_URL = "https://api.invertironline.com/token"
# cotización por título:  /api/v2/{mercado}/Titulos/{simbolo}/Cotizacion
QUOTE_URL = "https://api.invertironline.com/api/v2/bCBA/Titulos/{sym}/Cotizacion"


class IOLProvider(FeedProvider):
    name = "iol"

    def __init__(self):
        self.user = os.getenv("IOL_USER", "")
        self.password = os.getenv("IOL_PASSWORD", "")
        self.timeout = float(os.getenv("IOL_TIMEOUT", "8"))
        self._token: str | None = None
        self._exp = 0.0
        if not (self.user and self.password):
            raise RuntimeError("IOL no configurado: definí IOL_USER e IOL_PASSWORD.")

    def _token_get(self) -> str:
        if self._token and time.time() < self._exp - 30:
            return self._token
        with httpx.Client(timeout=self.timeout) as c:
            r = c.post(TOKEN_URL, data={
                "username": self.user, "password": self.password,
                "grant_type": "password"})
            r.raise_for_status()
            j = r.json()
        self._token = j["access_token"]
        self._exp = time.time() + float(j.get("expires_in", 800))
        return self._token

    def fetch(self) -> dict:
        from ..instruments import LECAPS, HD_BONDS
        symbols = [i["feed_symbol"] for i in LECAPS + HD_BONDS]
        headers = {"Authorization": f"Bearer {self._token_get()}"}
        arg_fi: dict = {}
        with httpx.Client(timeout=self.timeout, headers=headers) as c:
            for s in symbols:
                try:
                    r = c.get(QUOTE_URL.format(sym=s))
                    r.raise_for_status()
                    d = r.json()
                except Exception:
                    continue
                arg_fi[s] = Quote(
                    symbol=s,
                    last=d.get("ultimoPrecio"),
                    bid=(d.get("puntas") or [{}])[0].get("precioCompra") if d.get("puntas") else None,
                    ask=(d.get("puntas") or [{}])[0].get("precioVenta") if d.get("puntas") else None,
                    var_pct=d.get("variacion"),
                    volume=d.get("volumen"),
                    ts=self._now(),
                )
        return {"arg_fi": arg_fi, "arg_eq": {}, "arg_cedears": {},
                "usa_adrs": {}, "usa_stocks": {}}
