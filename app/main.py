"""
Backend NetFinance — Curvas en vivo (Tasa Fija en Pesos + Soberanos Hard Dólar).

Ejecutar:
    uvicorn app.main:app --reload --port 8000
Luego abrir http://localhost:8000
"""
from __future__ import annotations
import datetime as _dt
import threading
import time

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

from . import calc
from .config import get_provider, REFRESH_SECONDS, FEED
from .instruments import LECAPS, HD_BONDS, ACCIONES

app = FastAPI(title="NetFinance — Curvas en vivo")

_provider = get_provider()
_STATIC = os.path.join(os.path.dirname(__file__), "..", "static")

# --- caché simple de cotizaciones (evita golpear el feed en cada request) ---
_cache: dict[str, object] = {"ts": 0.0, "quotes": {}}
_lock = threading.Lock()

_ALL_SYMBOLS = [i["feed_symbol"] for i in LECAPS + HD_BONDS + ACCIONES]


def _quotes() -> dict:
    with _lock:
        if time.time() - _cache["ts"] < REFRESH_SECONDS and _cache["quotes"]:
            return _cache["quotes"]  # type: ignore
        try:
            q = _provider.fetch(_ALL_SYMBOLS)
        except Exception as e:  # feed caído: devolvemos lo último que haya
            if _cache["quotes"]:
                return _cache["quotes"]  # type: ignore
            raise RuntimeError(f"Feed '{FEED}' falló: {e}")
        _cache["quotes"] = q
        _cache["ts"] = time.time()
        return q


# ---------------------------------------------------------------------------
def _pesos_payload() -> dict:
    q = _quotes()
    hoy = _dt.date.today()
    rows = []
    for i in LECAPS:
        quote = q.get(i["feed_symbol"])
        px = quote.price if quote else None
        m = calc.lecap_metrics(px, i["vpv"], i["vencimiento"], hoy)
        rows.append({
            "ticker": i["ticker"], "tipo": i["tipo"],
            "vencimiento": i["vencimiento"], "dias": m["dias"],
            "precio": px, "vpv": i["vpv"],
            "tna": m["tna"], "tem": m["tem"], "tea": m["tea"],
            "var_pct": quote.var_pct if quote else None,
            "hora": quote.ts if quote else None,
        })
    rows.sort(key=lambda r: r["dias"] or 0)
    return {"tipo": "pesos", "feed": FEED, "asof": _dt.datetime.now().isoformat(timespec="seconds"),
            "rows": rows}


def _hd_payload() -> dict:
    q = _quotes()
    hoy = _dt.date.today()
    rows = []
    for i in HD_BONDS:
        quote = q.get(i["feed_symbol"])
        px = quote.price if quote else None
        m = calc.bond_metrics(px, i["schedule"], hoy)
        rows.append({
            "ticker": i["ticker"], "ley": i["ley"],
            "vencimiento": i["vencimiento"], "moneda": i["moneda"],
            "precio_limpio": px, "corridos": m["corridos"],
            "precio_sucio": m["precio_sucio"],
            "tir": m["tir"], "md": m["md"], "duration": m["duration"],
            "paridad": m["paridad"], "valor_residual": m["valor_residual"],
            "var_pct": quote.var_pct if quote else None,
            "hora": quote.ts if quote else None,
        })
    # ordenar por MD (para dibujar la curva TIR vs duration)
    rows.sort(key=lambda r: (r["md"] is None, r["md"] or 0))
    return {"tipo": "hd", "feed": FEED, "asof": _dt.datetime.now().isoformat(timespec="seconds"),
            "rows": rows}


@app.get("/api/curva-pesos")
def curva_pesos():
    return _pesos_payload()


@app.get("/api/curva-hd")
def curva_hd():
    return _hd_payload()


@app.get("/api/acciones")
def acciones():
    q = _quotes()
    rows = []
    num = den = 0.0          # para variación estimada ponderada por volumen
    suben = bajan = 0
    for i in ACCIONES:
        quote = q.get(i["feed_symbol"])
        px = quote.price if quote else None
        var = quote.var_pct if quote else None
        vol = quote.volume if quote else None
        if var is not None:
            if var > 0.01:
                suben += 1
            elif var < -0.01:
                bajan += 1
            w = vol if (vol and vol > 0) else 1.0
            num += var * w
            den += w
        rows.append({"ticker": i["ticker"], "nombre": i["nombre"],
                     "precio": px, "var_pct": var, "volumen": vol,
                     "hora": quote.ts if quote else None})
    merval_est = (num / den) if den else None
    con_datos = [r for r in rows if r["var_pct"] is not None]
    mejor = max(con_datos, key=lambda r: r["var_pct"], default=None)
    peor = min(con_datos, key=lambda r: r["var_pct"], default=None)
    rows.sort(key=lambda r: (r["var_pct"] is None, -(r["var_pct"] or 0)))
    return {"tipo": "acciones", "feed": FEED,
            "asof": _dt.datetime.now().isoformat(timespec="seconds"),
            "merval_est": merval_est, "suben": suben, "bajan": bajan,
            "mejor": mejor, "peor": peor, "rows": rows}


@app.get("/api/health")
def health():
    return {"ok": True, "feed": FEED, "refresh_s": REFRESH_SECONDS,
            "instrumentos": {"pesos": len(LECAPS), "hd": len(HD_BONDS),
                             "acciones": len(ACCIONES)}}


@app.get("/api/diag")
def diag():
    """Diagnóstico: qué símbolos resuelve el feed activo y cuáles faltan."""
    q = _quotes()
    def row(i):
        quote = q.get(i["feed_symbol"])
        return {"ticker": i["ticker"], "feed_symbol": i["feed_symbol"],
                "precio": quote.price if quote else None,
                "var_pct": quote.var_pct if quote else None,
                "encontrado": bool(quote and quote.price)}
    pesos = [row(i) for i in LECAPS]
    hd = [row(i) for i in HD_BONDS]
    acc = [row(i) for i in ACCIONES]
    ok = sum(1 for r in pesos + hd + acc if r["encontrado"])
    return {"feed": FEED, "encontrados": ok, "total": len(pesos) + len(hd) + len(acc),
            "pesos": pesos, "hd": hd, "acciones": acc}


@app.get("/")
def index():
    return FileResponse(os.path.join(_STATIC, "index.html"))


app.mount("/static", StaticFiles(directory=_STATIC), name="static")
