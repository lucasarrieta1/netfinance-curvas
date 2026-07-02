"""
Diagnóstico data912 — corré esto LOCAL (tenés red; el sandbox no).

    python check_data912.py

Te dice, de tu universo de instrumentos, cuáles devuelve data912 y con qué
precio, y cuáles faltan. Útil sobre todo para las variantes dólar de los HD
(AL30D, GD30D, ...): si aparecen muchas como FALTA, probá sumar otro panel en
app/feeds/data912.py (PANELS) o revisá el sufijo que usa data912.
"""
from app.feeds.data912 import Data912Provider, PANELS
from app.instruments import LECAPS, HD_BONDS

syms = [i["feed_symbol"] for i in LECAPS + HD_BONDS]
print(f"Consultando {len(syms)} símbolos en paneles {PANELS} ...\n")

prov = Data912Provider()
q = prov.fetch(syms)

def line(group, items):
    print(f"── {group} ──")
    for i in items:
        s = i["feed_symbol"]
        quote = q.get(s)
        if quote and quote.price:
            print(f"  ✓ {s:8} {quote.price:>10.3f}   var {quote.var_pct}")
        else:
            print(f"  ✗ {s:8} FALTA")
    print()

line("LECAP / BONCAP (pesos)", LECAPS)
line("Hard Dólar (ticker D)", HD_BONDS)

ok = sum(1 for s in syms if q.get(s) and q[s].price)
print(f"Encontrados con precio: {ok}/{len(syms)}")
