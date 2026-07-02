"""
Motor de cálculo de rendimientos — NetFinance.

Replica exactamente las convenciones de los Excel de Lucas:

LECAP / BONCAP (capitalizables, bullet):
    tasa_periodo = VPV / precio - 1
    TNA = tasa_periodo * 365 / dias
    TEM = (VPV / precio) ** (30 / dias) - 1
    TEA = (1 + TEM) ** 12 - 1

Bonos Hard Dollar (AL/GD/AE/AO/AN/BOPREAL):
    intereses corridos = renta_periodo_actual * dias_30_360(ultimo_cupon, liq) / 180
    precio_sucio = precio_limpio + intereses_corridos
    TIR (TEA) por XIRR Act/365 sobre el precio sucio
    Duration Macaulay = Σ (t_i * PV_i) / precio_sucio      (t en años Act/365)
    MD = Macaulay / (1 + TIR)
    Paridad = precio_limpio / (valor_residual + intereses_corridos)
"""
from __future__ import annotations
import datetime as _dt
from typing import Optional


# ----------------------------------------------------------------------
# Fechas
# ----------------------------------------------------------------------
def _d(x) -> _dt.date:
    if isinstance(x, _dt.datetime):
        return x.date()
    if isinstance(x, _dt.date):
        return x
    return _dt.date.fromisoformat(str(x)[:10])


def dias_30_360(f0: _dt.date, f1: _dt.date) -> int:
    """Días entre f0 y f1 según convención 30/360 (US NASD)."""
    d0, d1 = min(f0.day, 30), f1.day
    if d0 == 30 and d1 == 31:
        d1 = 30
    return (f1.year - f0.year) * 360 + (f1.month - f0.month) * 30 + (d1 - d0)


# ----------------------------------------------------------------------
# LECAP / BONCAP
# ----------------------------------------------------------------------
def lecap_metrics(precio: float, vpv: float, vto, liq: Optional[_dt.date] = None) -> dict:
    """Métricas de una letra/bono capitalizable a partir del precio de mercado."""
    liq = liq or _dt.date.today()
    vto = _d(vto)
    dias = (vto - liq).days              # act/365 para TNA
    dias_m = dias_30_360(liq, vto)       # 30/360 para TEM (convención del Excel)
    if precio is None or precio <= 0 or dias <= 0:
        return {"dias": dias, "tna": None, "tem": None, "tea": None,
                "tasa_periodo": None, "vpv": vpv}
    ratio = vpv / precio
    tasa_periodo = ratio - 1.0
    tna = tasa_periodo * 365.0 / dias
    tem = ratio ** (30.0 / dias_m) - 1.0 if dias_m > 0 else None
    tea = (1.0 + tem) ** 12 - 1.0 if tem is not None else None
    return {"dias": dias, "tna": tna, "tem": tem, "tea": tea,
            "tasa_periodo": tasa_periodo, "vpv": vpv}


# ----------------------------------------------------------------------
# Bonos con cupón + amortización (XIRR)
# ----------------------------------------------------------------------
def _xnpv(rate: float, flows: list[tuple[_dt.date, float]], t0: _dt.date) -> float:
    return sum(cf / (1.0 + rate) ** ((f - t0).days / 365.0) for f, cf in flows)


def xirr(flows: list[tuple[_dt.date, float]], t0: _dt.date,
         lo: float = -0.99, hi: float = 5.0) -> Optional[float]:
    """TIR (TEA) por bisección, Act/365. flows incluye el desembolso negativo en t0."""
    f_lo, f_hi = _xnpv(lo, flows, t0), _xnpv(hi, flows, t0)
    if f_lo * f_hi > 0:
        # ampliar el techo por si el bono rinde muchísimo
        hi = 20.0
        f_hi = _xnpv(hi, flows, t0)
        if f_lo * f_hi > 0:
            return None
    for _ in range(200):
        mid = (lo + hi) / 2.0
        f_mid = _xnpv(mid, flows, t0)
        if abs(f_mid) < 1e-10:
            return mid
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2.0


def bond_metrics(precio_limpio: float, schedule: list[dict],
                 liq: Optional[_dt.date] = None) -> dict:
    """
    Métricas de un bono HD a partir del precio limpio (USD c/100 VN) en vivo.

    schedule: lista de dicts con 'fecha' (ISO), 'renta', 'flujo_total',
              'valor_residual', 'estado'.  Se recalcula qué está pendiente
              respecto de la fecha de liquidación (no se confía en 'estado').
    """
    liq = liq or _dt.date.today()
    sched = sorted(schedule, key=lambda r: _d(r["fecha"]))

    # cupón del período en curso, fecha del último cupón <= liq y del próximo
    ultimo_cupon = None
    proximo_cupon = None
    renta_periodo = 0.0
    for r in sched:
        f = _d(r["fecha"])
        if f <= liq:
            ultimo_cupon = f
        else:
            proximo_cupon = f
            renta_periodo = r.get("renta") or 0.0
            break

    # intereses corridos (30/360), base = largo real del período de cupón
    # (sirve para cupones mensuales, trimestrales o semestrales por igual)
    corridos = 0.0
    if ultimo_cupon is not None and proximo_cupon is not None and renta_periodo:
        base = dias_30_360(ultimo_cupon, proximo_cupon) or 180
        corridos = renta_periodo * dias_30_360(ultimo_cupon, liq) / base

    if precio_limpio is None or precio_limpio <= 0:
        return {"precio_limpio": precio_limpio, "corridos": corridos,
                "precio_sucio": None, "tir": None, "md": None,
                "duration": None, "paridad": None, "valor_residual": None,
                "dias_al_vto": None}

    precio_sucio = precio_limpio + corridos

    # flujos futuros (estrictamente posteriores a la liquidación)
    futuros = [(_d(r["fecha"]), r["flujo_total"]) for r in sched
               if _d(r["fecha"]) > liq and r.get("flujo_total")]
    if not futuros:
        return {"precio_limpio": precio_limpio, "corridos": corridos,
                "precio_sucio": precio_sucio, "tir": None, "md": None,
                "duration": None, "paridad": None, "valor_residual": None,
                "dias_al_vto": None}

    flows = [(liq, -precio_sucio)] + futuros
    tir = xirr(flows, liq)

    duration = md = None
    if tir is not None:
        pv_tot = 0.0
        tpv = 0.0
        for f, cf in futuros:
            t = (f - liq).days / 365.0
            pv = cf / (1.0 + tir) ** t
            pv_tot += pv
            tpv += t * pv
        duration = tpv / pv_tot if pv_tot else None
        md = duration / (1.0 + tir) if duration is not None else None

    # valor residual vigente = residual remanente tras el último cupón pagado
    vr = 100.0
    for r in sched:
        if _d(r["fecha"]) <= liq and r.get("valor_residual") is not None:
            vr = r.get("valor_residual")

    paridad = precio_limpio / (vr + corridos) if vr else None
    dias_al_vto = (futuros[-1][0] - liq).days

    return {"precio_limpio": precio_limpio, "corridos": corridos,
            "precio_sucio": precio_sucio, "tir": tir, "md": md,
            "duration": duration, "paridad": paridad,
            "valor_residual": vr, "dias_al_vto": dias_al_vto}
