# NetFinance · Curvas en vivo

Terminal web de renta fija: **Tasa Fija en Pesos** (LECAP/BONCAP) y **Soberanos Hard Dólar**
(AL/GD/AE/AO/AN + BOPREAL), con precios en vivo y TNA/TEM/TEA/TIR/MD/paridad recalculadas
en el momento — replicando exactamente las convenciones de los Excel de NetFinance.

El precio es lo único que viene de afuera; todo el cálculo es propio y quedó **validado
al 4.º decimal contra el modelo Excel** (TIR, MD y paridad clavadas en los 14 bonos con precio;
TNA/TEM clavadas en las 11 letras/bonos capitalizables).

## Arranque rápido (demo offline)

```bash
pip install -r requirements.txt
cp .env.example .env        # queda FEED=mock por defecto
./run.sh                    # o: uvicorn app.main:app --reload --port 8000
```

Abrir http://localhost:8000 . Con `FEED=mock` la web anda sin red, usando los últimos
precios del Excel con un pequeño ruido para que se vea viva.

## Cambiar de proveedor de precios

Se cambia **una** variable en `.env` (`FEED=...`). El resto del sistema no se toca:

| FEED | Qué es | Notas |
|------|--------|-------|
| `mock` | Demo offline (últimos precios del Excel) | Sin red. Para desarrollar el front. |
| `data912` | API pública gratuita | Prototipo. **No es real-time** (caché ~2 h). |
| `iol` | Broker IOL, tiempo real | Requiere `IOL_USER` / `IOL_PASSWORD`. |
| `byma` | **BYMA Market Data oficial** | Producción. Requiere credenciales del portal. |

## Conectar BYMA Market Data (producción)

Con tu suscripción paga:

1. Entrá al **Portal de Desarrolladores**: https://apiportal.byma.com.ar
   Registrate, creá una *aplicación* y obtené `CLIENT_ID` y `CLIENT_SECRET`.
2. Del manual del portal sacás **3 datos** y los cargás en `.env`:
   - `BYMA_TOKEN_URL` → endpoint OAuth para pedir el token
   - `BYMA_MD_URL` → endpoint de Market Data de renta fija (snapshot/panel)
   - `BYMA_CLIENT_ID` / `BYMA_CLIENT_SECRET`
3. En `app/feeds/byma.py` hay 3 marcas `# TODO` para ajustar:
   `(1)` el *scope* del token si el portal lo exige, `(2)` la forma del endpoint
   (panel completo vs. por símbolo) y `(3)` el nombre real de los campos del payload.
4. `FEED=byma` y listo.

> **Redistribución:** consumir el dato internamente es una cosa; mostrarlo a clientes
> (web pública, placas, WhatsApp) es otra. Confirmá los términos de redistribución de
> tu suscripción con el Centro de Atención de BYMA antes de exponerlo hacia afuera.

## Mapeo de símbolos

- LECAP/BONCAP → se piden en **pesos** con el ticker tal cual (`S17L6`, `T30J7`, …).
- Hard Dólar → se piden con el ticker **"D"** (precio en USD/MEP: `AL30D`, `GD30D`, …),
  igual que la columna *Px USD* del Excel. Ver `feed_symbol` en `app/instruments.py`.

Si un proveedor usa otro sufijo o mercado para el precio dólar, se ajusta ahí sin tocar
el resto.

## Estructura

```
app/
  main.py         FastAPI: /api/curva-pesos, /api/curva-hd, /api/health
  calc.py         motor de cálculo (LECAP + XIRR/duration)  ← validado vs Excel
  instruments.py  universo: tabla LECAP/BONCAP + carga de bonos HD
  config.py       selección de feed (una variable)
  data/hd_bonds.json   flujos de fondos extraídos del Excel
  feeds/
    base.py       interfaz FeedProvider + dataclass Quote
    mock.py       demo offline
    data912.py    API pública (prototipo)
    iol.py        broker IOL (real-time)
    byma.py       BYMA Market Data oficial (producción)  ← 3 TODO para completar
static/index.html  terminal web (curvas + tablas)
```

## Notas de cálculo

- **LECAP/BONCAP:** `tasa_periodo = VPV/precio − 1`; `TNA = tasa_periodo·365/días` (act/365);
  `TEM = (VPV/precio)^(30/días_30/360) − 1`; `TEA = (1+TEM)¹² − 1`.
  (La TNA usa días calendario y la TEM días 30/360, tal como el Excel.)
- **Hard Dólar:** intereses corridos 30/360 sobre el largo real del período de cupón;
  precio sucio = limpio + corridos; **TIR (TEA)** por XIRR act/365; Macaulay = Σ(t·PV)/sucio;
  **MD = Macaulay/(1+TIR)**; paridad = limpio/(valor residual + corridos).
- Los flujos futuros se recalculan contra la fecha de liquidación del día, así que las
  métricas ruedan solas a medida que van venciendo cupones.
```


## Paneles

Además de las dos curvas de renta fija, el terminal incluye paneles de precio +
variación (barras + tabla) que salen del mismo feed: Acciones Argentinas (panel
líder + Merval estimado), Bonos CER, CEDEARs, ADRs y Acciones EE.UU. (índices vía
ETF SPY/QQQ/DIA). El header muestra dólar MEP y CCL. Los universos son listas
editables en `app/instruments.py`. Para agregar otro panel-lista, sumá una entrada
en `LISTAS` y una pestaña en `static/index.html`.

Los mercados están scopeados (arg_fi / arg_eq / arg_cedears / usa_adrs /
usa_stocks) para que no se pisen tickers que existen en varios (GGAL local vs ADR,
AAPL CEDEAR vs acción USA).

## Deploy (Render — recomendado)

Este NO es un sitio estático: tiene backend Python. **Netlify no sirve** (da 404
porque no puede correr el servidor). Usá un host que ejecute Python:

**Render (gratis):**
1. Subí esta carpeta a un repo de GitHub.
2. En render.com → *New* → *Blueprint* → conectá el repo. Render lee `render.yaml`.
3. Levanta solo. Cambiás `FEED` (mock → data912 → byma) desde *Environment* en el panel.

El mismo servicio sirve el front y la API (mismo dominio → sin CORS).

**Railway (alternativa, sin Git):** `npm i -g @railway/cli && railway up` desde la carpeta.
Usa el `Procfile`. Cargá las env vars (`FEED`, etc.) en el panel.

**Fly.io / cualquier VPS:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

> Nota: el plan free de Render "duerme" el servicio tras unos minutos de inactividad
> y tarda ~30 s en despertar en la primera visita. Para uso interno alcanza; si querés
> que esté siempre activo, es el plan pago más barato.
