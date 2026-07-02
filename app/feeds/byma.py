"""
BymaProvider — feed OFICIAL de BYMA Market Data (para suscriptor pago).

Este es el proveedor de PRODUCCIÓN.  El flujo, según el Manual del Portal de
Desarrolladores de BYMA (apiportal.byma.com.ar), es:

  1. Registrarte en el portal y crear una "aplicación" -> obtenés
     CLIENT_ID y CLIENT_SECRET.
  2. Pedir un token de seguridad (OAuth2 client_credentials).
  3. Llamar a los endpoints REST de Market Data con  Authorization: Bearer <token>.

Hay ambiente de HOMOLOGACIÓN y de PRODUCCIÓN.  Los paths exactos de los
endpoints y los nombres de los campos están en la documentación del portal
(detrás del login del suscriptor) — por eso quedan marcados con  # TODO.
Cuando los tengas, completás las 3 marcas y el resto del sistema anda igual.

Configuración por variables de entorno (.env):
  BYMA_TOKEN_URL, BYMA_MD_URL, BYMA_CLIENT_ID, BYMA_CLIENT_SECRET
  BYMA_ENV = homologacion | produccion
"""
from __future__ import annotations
import os
import time
import httpx
from .base import FeedProvider, Quote


class BymaProvider(FeedProvider):
    name = "byma"

    def __init__(self):
        self.token_url = os.getenv("BYMA_TOKEN_URL", "")
        self.md_url = os.getenv("BYMA_MD_URL", "")
        self.client_id = os.getenv("BYMA_CLIENT_ID", "")
        self.client_secret = os.getenv("BYMA_CLIENT_SECRET", "")
        self.timeout = float(os.getenv("BYMA_TIMEOUT", "8"))
        self._token: str | None = None
        self._token_exp: float = 0.0
        if not (self.token_url and self.md_url and self.client_id):
            raise RuntimeError(
                "BYMA no configurado. Definí BYMA_TOKEN_URL, BYMA_MD_URL, "
                "BYMA_CLIENT_ID y BYMA_CLIENT_SECRET en el .env "
                "(ver Manual del Portal de Desarrolladores BYMA)."
            )

    # ------------------------------------------------------------------
    # Token OAuth2 (client_credentials), cacheado hasta que expira
    # ------------------------------------------------------------------
    def _get_token(self) -> str:
        if self._token and time.time() < self._token_exp - 30:
            return self._token
        with httpx.Client(timeout=self.timeout) as c:
            resp = c.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    # "scope": "market-data",   # TODO(1): scope si el portal lo pide
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            j = resp.json()
        self._token = j["access_token"]
        self._token_exp = time.time() + float(j.get("expires_in", 300))
        return self._token

    # ------------------------------------------------------------------
    # Market Data
    # ------------------------------------------------------------------
    def fetch(self, symbols: list[str]) -> dict[str, Quote]:
        token = self._get_token()
        headers = {"Authorization": f"Bearer {token}", "accept": "application/json"}
        out: dict[str, Quote] = {}
        with httpx.Client(timeout=self.timeout, headers=headers) as c:
            # TODO(2): ajustar al endpoint real de renta fija del portal.
            # Suele ser un panel completo (traés todo y filtrás) o por símbolo.
            resp = c.get(self.md_url)          # p.ej. .../market-data/v1/snapshot/fixed-income
            resp.raise_for_status()
            data = resp.json()

        rows = data if isinstance(data, list) else data.get("data", data.get("items", []))
        want = set(symbols)
        for row in rows:
            # TODO(3): mapear los nombres de campo reales del payload BYMA.
            sym = row.get("symbol") or row.get("ticker")
            if not sym or sym not in want:
                continue
            out[sym] = Quote(
                symbol=sym,
                last=row.get("last") or row.get("closingPrice") or row.get("trade"),
                bid=row.get("bidPrice") or row.get("bid"),
                ask=row.get("offerPrice") or row.get("ask"),
                prev_close=row.get("previousClosingPrice") or row.get("prevClose"),
                var_pct=row.get("dailyVariation") or row.get("varPct"),
                volume=row.get("volume") or row.get("volumeAmount"),
                ts=self._now(),
            )
        return out
