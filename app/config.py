"""
Selección del proveedor de precios.

Cambiás UNA variable de entorno (FEED) y todo el sistema usa otro feed:
    FEED=mock      -> demo offline con últimos precios del Excel (default)
    FEED=data912   -> API pública gratuita (prototipo, NO real-time)
    FEED=iol       -> broker IOL, tiempo real (requiere IOL_USER/IOL_PASSWORD)
    FEED=byma      -> BYMA Market Data oficial (requiere credenciales del portal)

El resto del código (cálculo, endpoints, front) no cambia.
"""
from __future__ import annotations
import os
from .feeds.base import FeedProvider
from .feeds.mock import MockProvider

FEED = os.getenv("FEED", "mock").lower()
REFRESH_SECONDS = int(os.getenv("REFRESH_SECONDS", "15"))


def get_provider() -> FeedProvider:
    if FEED == "mock":
        return MockProvider()
    if FEED == "data912":
        from .feeds.data912 import Data912Provider
        return Data912Provider()
    if FEED == "iol":
        from .feeds.iol import IOLProvider
        return IOLProvider()
    if FEED == "byma":
        from .feeds.byma import BymaProvider
        return BymaProvider()
    raise ValueError(f"FEED desconocido: {FEED!r}")
