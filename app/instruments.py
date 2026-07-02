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
     "feed_symbol": t, "moneda": "ARS", "px_ref": px}
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
    {"ticker": t, "nombre": n, "feed_symbol": t, "moneda": "ARS", "px_ref": px}
    for (t, n, px) in _ACCIONES_ROWS
]

# Índice símbolo_feed -> precio_ref, para el MockProvider
PX_REF = {i["feed_symbol"]: i["px_ref"] for i in LECAPS + HD_BONDS + ACCIONES
          if i["px_ref"] is not None}
