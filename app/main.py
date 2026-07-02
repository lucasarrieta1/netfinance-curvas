"""
Backend NetFinance — Terminal en vivo.

Pestañas: Tasa Fija en Pesos · Soberanos Hard Dólar · Acciones Argentinas ·
CEDEARs · ADRs · Acciones EE.UU. — todo sobre el mismo feed.

Ejecutar:
    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations
import datetime as _dt
import threading
import time
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import calc
from .config import get_provider, REFRESH_SECONDS, FEED
from .instruments import LECAPS, HD_BONDS, ACCIONES, LISTAS

app = FastAPI(title="NetFinance — Terminal en vivo")

_provider = get_provider()
_STATIC = os.path.join(os.path.dirname(__file__), "..", "static")

# --- caché de cotizaciones (snapshot anidado por mercado) + fx ---
_cache = {"ts": 0.0, "quotes": {}, "fx_ts": 0.0, "fx": {"mep": None, "ccl": None}}
_lock = threading.Lock()


def _quotes() -> dict:
    with _lock:
        if time.time() - _cache["ts"] < REFRESH_SECONDS and _cache["quotes"]:
            return _cache["quotes"]
        try:
            q = _provider.fetch()
        except Exception as e:
            if _cache["quotes"]:
                return _cache["quotes"]
            raise RuntimeError(f"Feed '{FEED}' falló: {e}")
        _cache["quotes"] = q
        _cache["ts"] = time.time()
        return q


def _fx() -> dict:
    with _lock:
        if time.time() - _cache["fx_ts"] < REFRESH_SECONDS and _cache["fx_ts"]:
            return _cache["fx"]
        try:
            fx = _provider.fetch_fx()
        except Exception:
            return _cache["fx"]
        _cache["fx"] = fx
        _cache["fx_ts"] = time.time()
        return fx


def _q(quotes, market, symbol):
    return quotes.get(market, {}).get(symbol)


def _asof():
    return _dt.datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
def _pesos_payload() -> dict:
    q = _quotes(); hoy = _dt.date.today(); rows = []
    for i in LECAPS:
        quote = _q(q, i["market"], i["feed_symbol"])
        px = quote.price if quote else None
        m = calc.lecap_metrics(px, i["vpv"], i["vencimiento"], hoy)
        rows.append({"ticker": i["ticker"], "tipo": i["tipo"],
                     "vencimiento": i["vencimiento"], "dias": m["dias"],
                     "precio": px, "vpv": i["vpv"],
                     "tna": m["tna"], "tem": m["tem"], "tea": m["tea"],
                     "var_pct": quote.var_pct if quote else None})
    rows.sort(key=lambda r: r["dias"] or 0)
    return {"tipo": "pesos", "feed": FEED, "asof": _asof(), "rows": rows}


def _hd_payload() -> dict:
    q = _quotes(); hoy = _dt.date.today(); rows = []
    for i in HD_BONDS:
        quote = _q(q, i["market"], i["feed_symbol"])
        px = quote.price if quote else None
        m = calc.bond_metrics(px, i["schedule"], hoy)
        rows.append({"ticker": i["ticker"], "ley": i["ley"],
                     "vencimiento": i["vencimiento"], "moneda": i["moneda"],
                     "precio_limpio": px, "corridos": m["corridos"],
                     "precio_sucio": m["precio_sucio"], "tir": m["tir"],
                     "md": m["md"], "duration": m["duration"],
                     "paridad": m["paridad"], "valor_residual": m["valor_residual"],
                     "var_pct": quote.var_pct if quote else None})
    rows.sort(key=lambda r: (r["md"] is None, r["md"] or 0))
    return {"tipo": "hd", "feed": FEED, "asof": _asof(), "rows": rows}


def _breadth(rows):
    """Suben/bajan/mejor/peor/variación ponderada por volumen."""
    num = den = 0.0; suben = bajan = 0
    for r in rows:
        v = r["var_pct"]
        if v is None:
            continue
        if v > 0.01: suben += 1
        elif v < -0.01: bajan += 1
        w = r["volumen"] if (r["volumen"] and r["volumen"] > 0) else 1.0
        num += v * w; den += w
    con = [r for r in rows if r["var_pct"] is not None]
    return {"suben": suben, "bajan": bajan,
            "prom_pond": (num / den) if den else None,
            "mejor": max(con, key=lambda r: r["var_pct"], default=None),
            "peor": min(con, key=lambda r: r["var_pct"], default=None)}


@app.get("/api/curva-pesos")
def curva_pesos(): return _pesos_payload()


@app.get("/api/curva-hd")
def curva_hd(): return _hd_payload()


@app.get("/api/acciones")
def acciones():
    q = _quotes(); rows = []
    for i in ACCIONES:
        quote = _q(q, i["market"], i["feed_symbol"])
        rows.append({"ticker": i["ticker"], "nombre": i["nombre"],
                     "precio": quote.price if quote else None,
                     "var_pct": quote.var_pct if quote else None,
                     "volumen": quote.volume if quote else None})
    b = _breadth(rows)
    rows.sort(key=lambda r: (r["var_pct"] is None, -(r["var_pct"] or 0)))
    return {"tipo": "acciones", "feed": FEED, "asof": _asof(),
            "merval_est": b["prom_pond"], "suben": b["suben"], "bajan": b["bajan"],
            "mejor": b["mejor"], "peor": b["peor"], "rows": rows}


@app.get("/api/lista/{key}")
def lista(key: str):
    """Panel genérico de precio + variación (CEDEARs, ADRs, USA)."""
    cfg = LISTAS.get(key)
    if not cfg:
        raise HTTPException(404, f"lista '{key}' no existe")
    q = _quotes(); rows = []
    for i in cfg["items"]:
        quote = _q(q, i["market"], i["feed_symbol"])
        rows.append({"ticker": i["ticker"], "nombre": i["nombre"],
                     "moneda": i["moneda"], "precio": quote.price if quote else None,
                     "var_pct": quote.var_pct if quote else None,
                     "volumen": quote.volume if quote else None})
    b = _breadth(rows)
    rows.sort(key=lambda r: (r["var_pct"] is None, -(r["var_pct"] or 0)))
    return {"tipo": key, "titulo": cfg["titulo"], "sub": cfg["sub"],
            "nota": cfg.get("nota"), "index_label": cfg.get("index_label", "Variación prom."),
            "index_sub": cfg.get("index_sub", "ponderada por volumen"),
            "feed": FEED, "asof": _asof(),
            "suben": b["suben"], "bajan": b["bajan"], "prom_pond": b["prom_pond"],
            "mejor": b["mejor"], "peor": b["peor"], "rows": rows}


@app.get("/api/fx")
def fx():
    d = _fx()
    return {"mep": d.get("mep"), "ccl": d.get("ccl"), "feed": FEED, "asof": _asof()}


@app.get("/api/health")
def health():
    return {"ok": True, "feed": FEED, "refresh_s": REFRESH_SECONDS,
            "listas": list(LISTAS.keys()),
            "instrumentos": {"pesos": len(LECAPS), "hd": len(HD_BONDS),
                             "acciones": len(ACCIONES),
                             **{k: len(v["items"]) for k, v in LISTAS.items()}}}


@app.get("/api/diag")
def diag():
    q = _quotes()
    def row(i):
        quote = _q(q, i["market"], i["feed_symbol"])
        return {"ticker": i["ticker"], "market": i["market"],
                "precio": quote.price if quote else None,
                "encontrado": bool(quote and quote.price)}
    grupos = {"pesos": LECAPS, "hd": HD_BONDS, "acciones": ACCIONES}
    grupos.update({k: v["items"] for k, v in LISTAS.items()})
    data = {g: [row(i) for i in items] for g, items in grupos.items()}
    ok = sum(1 for rs in data.values() for r in rs if r["encontrado"])
    total = sum(len(rs) for rs in data.values())
    return {"feed": FEED, "encontrados": ok, "total": total, **data}


@app.get("/")
def index(): return FileResponse(os.path.join(_STATIC, "index.html"))


app.mount("/static", StaticFiles(directory=_STATIC), name="static")
