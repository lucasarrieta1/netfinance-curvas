"""
Universo de instrumentos.

- LECAP / BONCAP: tabla fija (ticker, tipo, vencimiento, VPV).  El VPV es el
  valor de pago al vencimiento por 100 VN, fijado en la emisión.
- Hard Dollar: se cargan desde app/data/hd_bonds.json (flujos extraídos del
  Excel de Lucas).

`feed_symbol` es el símbolo con el que se le pide el precio al proveedor:
  - LECAP/BONCAP -> ticker en pesos (S17L6, T30J7, ...)
  - Hard Dollar  -> ticker "D" (precio en USD / MEP: AL30D, GD30D, ...)
`px_ref` es el último precio conocido (del Excel), usado por el MockProvider
y como fallback si el feed no devuelve el instrumento.
"""
from __future__ import annotations
import json
import os

_DATA = os.path.join(os.path.dirname(__file__), "data", "hd_bonds.json")

# --- LECAP (S) y BONCAP (T) ------------------------------------------------
# (ticker, tipo, vencimiento ISO, VPV, precio_ref_ARS)
_LECAP_ROWS = [
    ("S17L6", "LECAP",  "2026-07-17", 107.920, 106.970),
    ("S31L6", "LECAP",  "2026-07-31", 117.680, 115.749),
    ("S14G6", "LECAP",  "2026-08-14", 108.030, 105.330),
    ("S31G6", "LECAP",  "2026-08-31", 127.060, 122.750),
    ("S30S6", "LECAP",  "2026-09-30", 117.536, 111.250),
    ("S30O6", "LECAP",  "2026-10-30", 135.278, 125.800),
    ("S30N6", "LECAP",  "2026-11-30", 129.890, 118.800),
    ("T15E7", "BONCAP", "2027-01-15", 161.100, 144.000),
    ("T30A7", "BONCAP", "2027-04-30", 157.340, 130.101),
    ("T31Y7", "BONCAP", "2027-05-31", 151.560, 124.200),
    ("T30J7", "BONCAP", "2027-06-30", 156.040, 125.300),
]

LECAPS = [
    {"ticker": t, "tipo": tipo, "vencimiento": v, "vpv": vpv,
     "feed_symbol": t, "market": "arg_fi", "moneda": "ARS", "px_ref": px}
    for (t, tipo, v, vpv, px) in _LECAP_ROWS
]


def _iso(s):
    """Convierte 'dd/mm/aaaa' -> 'aaaa-mm-dd'. Deja pasar ISO o None."""
    if not s or not isinstance(s, str):
        return s
    if "/" in s:
        d, m, y = s.split("/")
        return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
    return s


def load_hd_bonds() -> list[dict]:
    with open(_DATA, encoding="utf-8") as f:
        raw = json.load(f)
    out = []
    for name, b in raw.items():
        if name.startswith("BP"):        # excluir BOPREAL
            continue
        out.append({
            "ticker": name,
            "feed_symbol": name + "D",          # precio en dólares (MEP)
            "market": "arg_fi",
            "moneda": "USD",
            "ley": b.get("ley"),
            "vencimiento": _iso(b.get("vencimiento")),
            "cupon": b.get("cupon"),
            "amortizacion": b.get("amortizacion"),
            "schedule": b.get("schedule", []),
            "px_ref": b.get("ref_precio_limpio"),
        })
    return out


HD_BONDS = load_hd_bonds()

# --- Acciones · Panel Líder (S&P Merval) --------------------------------
# Composición del panel líder (se revisa por trimestre). Editá esta lista si
# BYMA/S&P cambia constituyentes. px_ref = valor indicativo solo para el mock.
_ACCIONES_ROWS = [
    ("ALUA",  "Aluar",                       900.0),
    ("BBAR",  "Banco BBVA Argentina",       8000.0),
    ("BMA",   "Banco Macro",               12000.0),
    ("BYMA",  "BYMA",                         500.0),
    ("CEPU",  "Central Puerto",             1800.0),
    ("COME",  "Soc. Comercial del Plata",    200.0),
    ("CRES",  "Cresud",                      2200.0),
    ("EDN",   "Edenor",                      3500.0),
    ("GGAL",  "Grupo Financiero Galicia",    7000.0),
    ("LOMA",  "Loma Negra",                  3000.0),
    ("METR",  "Metrogas",                    2500.0),
    ("MIRG",  "Mirgor",                     25000.0),
    ("PAMP",  "Pampa Energía",               4500.0),
    ("SUPV",  "Grupo Supervielle",           4000.0),
    ("TECO2", "Telecom Argentina",           3500.0),
    ("TGNO4", "Transp. Gas del Norte",       3000.0),
    ("TGSU2", "Transp. Gas del Sur",         7000.0),
    ("TRAN",  "Transener",                   2500.0),
    ("TXAR",  "Ternium Argentina",            900.0),
    ("VALO",  "Grupo Fin. Valores",           400.0),
    ("YPFD",  "YPF",                        45000.0),
]

ACCIONES = [
    {"ticker": t, "nombre": n, "feed_symbol": t, "market": "arg_eq",
     "moneda": "ARS", "px_ref": px}
    for (t, n, px) in _ACCIONES_ROWS
]

# --- CEDEARs (los más operados) -----------------------------------------
_CEDEARS_ROWS = [
    ("AAPL", "Apple"), ("MSFT", "Microsoft"), ("NVDA", "NVIDIA"),
    ("AMZN", "Amazon"), ("GOOGL", "Alphabet"), ("META", "Meta"),
    ("TSLA", "Tesla"), ("MELI", "MercadoLibre"), ("KO", "Coca-Cola"),
    ("AMD", "AMD"), ("NFLX", "Netflix"), ("BABA", "Alibaba"),
    ("JPM", "JPMorgan"), ("WMT", "Walmart"), ("DISN", "Disney"),
    ("PBR", "Petrobras"), ("VIST", "Vista Energy"), ("TSM", "TSMC"),
    ("BRKB", "Berkshire H."), ("XOM", "Exxon"), ("PFE", "Pfizer"),
    ("SPY", "S&P 500 ETF"), ("QQQ", "Nasdaq 100 ETF"),
]

# --- ADRs argentinos en USA ---------------------------------------------
_ADRS_ROWS = [
    ("GGAL", "Grupo Galicia"), ("YPF", "YPF"), ("BMA", "Banco Macro"),
    ("PAM", "Pampa Energía"), ("BBAR", "BBVA Argentina"), ("CEPU", "Central Puerto"),
    ("CRESY", "Cresud"), ("EDN", "Edenor"), ("TEO", "Telecom"),
    ("TGS", "Transp. Gas Sur"), ("SUPV", "Supervielle"), ("LOMA", "Loma Negra"),
    ("IRS", "IRSA"), ("VIST", "Vista Energy"),
]

# --- Acciones USA (líderes; el "índice" es la variación estimada) --------
_USA_ROWS = [
    ("AAPL", "Apple"), ("MSFT", "Microsoft"), ("NVDA", "NVIDIA"),
    ("AMZN", "Amazon"), ("GOOGL", "Alphabet"), ("META", "Meta"),
    ("TSLA", "Tesla"), ("AMD", "AMD"), ("NFLX", "Netflix"),
    ("JPM", "JPMorgan"), ("KO", "Coca-Cola"), ("DIS", "Disney"),
    ("BAC", "Bank of America"), ("XOM", "Exxon"), ("WMT", "Walmart"),
    ("V", "Visa"), ("MA", "Mastercard"), ("PG", "Procter & Gamble"),
]


def _mk(rows, market, moneda, px=100.0):
    return [{"ticker": t, "nombre": n, "feed_symbol": t, "market": market,
             "moneda": moneda, "px_ref": px} for (t, n) in rows]


CEDEARS = _mk(_CEDEARS_ROWS, "arg_cedears", "ARS", 20000.0)
ADRS    = _mk(_ADRS_ROWS,    "usa_adrs",    "USD", 25.0)
USA     = _mk(_USA_ROWS,     "usa_stocks",  "USD", 200.0)

# Registro de paneles-lista genéricos (precio + variación).
# index_label: rótulo del KPI de variación agregada (estilo "Merval est.").
LISTAS = {
    "cedears": {"titulo": "CEDEARs", "sub": "los más operados · precio en ARS y variación",
                "items": CEDEARS, "index_label": "Variación prom.",
                "index_sub": "ponderada por volumen", "nota": None},
    "adrs":    {"titulo": "ADRs argentinos", "sub": "listados en EE.UU. · precio en USD y variación",
                "items": ADRS, "index_label": "Variación prom.",
                "index_sub": "ponderada por volumen", "nota": None},
    "usa":     {"titulo": "Acciones EE.UU.", "sub": "líderes del mercado · precio en USD y variación",
                "items": USA, "index_label": "EE.UU. (est.)",
                "index_sub": "prom. pond. de líderes USA",
                "nota": "Índice estimado (prom. ponderado por volumen de las líderes); "
                        "data912 no expone el nivel oficial de los índices."},
}

# Registro GLOBAL de instrumentos (para el MockProvider y para diag).
REGISTRY = []
for _grp in [LECAPS, HD_BONDS, ACCIONES, CEDEARS, ADRS, USA]:
    for _i in _grp:
        REGISTRY.append({"market": _i["market"], "feed_symbol": _i["feed_symbol"],
                         "px_ref": _i.get("px_ref")})
