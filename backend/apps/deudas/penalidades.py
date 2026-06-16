"""
Calculo de penalidades tributarias del Impuesto Predial: REAJUSTE e INTERES
MORATORIO.

Replica las reglas del sistema legacy SIAP (SQL Server), calibradas contra
reportes reales de "Estado de Cuenta del Contribuyente" (PDFs oficiales).

Reglas de negocio
-----------------
REAJUSTE  (fuente: TABREAJUSTE, para TODOS los años)
  * Trimestre 1: SIEMPRE exento (no se reajusta la 1ra cuota).
  * El factor de cada (anio, trimestre) se lee de TABREAJUSTE. ReajFact viene
    en PORCENTAJE, asi que el reajuste de la cuota es:
        reajuste = cuota_base * ReajFact / 100
  * Por que la tabla y no IPM en vivo: SIAP usa el IPM internamente para
    CALCULAR el factor y lo "congela" en TABREAJUSTE cuando cada trimestre
    vence. Verificado contra datos reales:
        TABREAJUSTE(2026, T2) = 4.57137
        (IPM[abr2026] / IPM[feb2026] - 1) * 100 = 4.5716  --> coinciden
    Leer la tabla devuelve el valor EXACTO que cobra SIAP. Si un trimestre del
    año en curso aun no vencio, no tiene fila -> reajuste 0 (no se cobra aun).
    Esto reproduce el comportamiento real: el 14/05 el T2-2026 valia 0 y el
    01/06 (ya vencido) paso a 8.37.

INTERES MORATORIO  (fuente: TABTIM, solo años ANTERIORES al año en curso)
  * El año EN CURSO no genera interes moratorio, solo reajuste (verificado:
    interes 2026 = 0.00 en los reportes). El interes corre para cuotas
    vencidas en años anteriores.
  * Se acumula por los dias de atraso desde el dia siguiente al vencimiento
    hasta la fecha de pago (inclusive).
  * Tasa diaria = TIMFact / 30 (TIMFact es % mensual). Se acumula mes a mes
    porque la TIM cambia en el tiempo (0.90% hasta 2022, 0.70% desde 2023):
        interes = base * SUMA_por_mes( (TIM_diaria_mes / 100) * dias_del_mes )
  * El reajuste NO forma parte de la base del interes.
  * Es el "interes real matematico". Bajo AMNISTIA la capa de presentacion lo
    condona (pone 0): el monto a pagar es Base + Reajuste + Formulario.

Calibracion del reajuste (datos reales):
    año  base_anual  reajuste_PDF  reajuste_calc   (fuente)
    2021   899.97       40.82         40.80         estatico cerrado
    2022   926.73       42.79         42.77         estatico cerrado
    2025   719.08        0.07          0.07         estatico cerrado (10871)
    2026   732.27        8.37          8.37         año en curso (T2 vencido)
"""
from __future__ import annotations

import calendar
import datetime
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from apps.externos_muni.models import TabIpm, TabReajuste, TabTim


CENTAVO = Decimal("0.01")
CIEN = Decimal("100")
TREINTA = Decimal("30")

# trimestre -> mes de vencimiento estandar del Impuesto Predial
MES_VENCIMIENTO_TRIMESTRE = {1: 2, 2: 5, 3: 8, 4: 11}


def _q(valor) -> Decimal:
    """Redondea a 2 decimales (ROUND_HALF_UP) trabajando siempre en Decimal."""
    return Decimal(str(valor)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _d(valor) -> Decimal:
    """Convierte a Decimal sin perder precision (pasando por str)."""
    return Decimal(str(valor)) if not isinstance(valor, Decimal) else valor


# ---------------------------------------------------------------------------
# Cache de tablas de referencia. Son historicas/inmutables (append-only), asi
# que cargarlas 1 vez por proceso es seguro y evita N consultas en los loops
# de interes mes-a-mes. Mismo patron que _PREDIOCOND_CACHE en services.py.
# ---------------------------------------------------------------------------
_CACHE: dict[str, object] = {"ipm": None, "reaj": None, "tim": None, "tim_orden": None}


def limpiar_cache() -> None:
    """Resetea los caches (util en tests o si se recargan las tablas)."""
    _CACHE["ipm"] = None
    _CACHE["reaj"] = None
    _CACHE["tim"] = None
    _CACHE["tim_orden"] = None


def _ipm_cache() -> dict[tuple[int, int], Decimal]:
    if _CACHE["ipm"] is None:
        data: dict[tuple[int, int], Decimal] = {}
        qs = (
            TabIpm.objects.using("muni_db")
            .exclude(ipmanu="X")
            .values_list("ipmano", "ipmmes", "ipmvalor")
        )
        for ano, mes, val in qs:
            data[(int(ano), int(mes))] = _d(val)
        _CACHE["ipm"] = data
    return _CACHE["ipm"]  # type: ignore[return-value]


def _reaj_cache() -> dict[tuple[int, int], Decimal]:
    if _CACHE["reaj"] is None:
        data: dict[tuple[int, int], Decimal] = {}
        qs = (
            TabReajuste.objects.using("muni_db")
            .exclude(reajanu="X")
            .values_list("reajano", "reajtrim", "reajfact")
        )
        for ano, trim, fact in qs:
            data[(int(ano), int(trim))] = _d(fact)
        _CACHE["reaj"] = data
    return _CACHE["reaj"]  # type: ignore[return-value]


def _tim_cache() -> dict[tuple[int, int], Decimal]:
    if _CACHE["tim"] is None:
        data: dict[tuple[int, int], Decimal] = {}
        qs = (
            TabTim.objects.using("muni_db")
            .exclude(timanu="X")
            .values_list("timano", "timmes", "timfact")
        )
        for ano, mes, fact in qs:
            data[(int(ano), int(mes))] = _d(fact)
        _CACHE["tim"] = data
        # lista ordenada de claves para el fallback "ultima tasa conocida"
        _CACHE["tim_orden"] = sorted(data.keys())
    return _CACHE["tim"]  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------


def _ipm_valor(anio: int, mes: int) -> Decimal | None:
    return _ipm_cache().get((anio, mes))


def _reajuste_factor(anio: int, trimestre: int) -> Decimal | None:
    return _reaj_cache().get((anio, trimestre))


def variacion_ipm_porcentaje(
    anio_curso: int, fecha_pago: datetime.date
) -> Decimal | None:
    """
    DIAGNOSTICO / referencia. Devuelve la variacion acumulada del IPM (en %)
    desde Febrero del año en curso hasta el mes anterior al pago:

        (IPM[mes_anterior_al_pago] / IPM[febrero] - 1) * 100

    Es la formula que SIAP usa INTERNAMENTE para calcular y "congelar" el
    factor de TABREAJUSTE del año en curso. No se usa para cobro (eso sale de
    TABREAJUSTE via _calcular_reajuste); queda como utilidad de validacion.
    Devuelve None si falta algun IPM (ej. el mes aun no fue publicado).
    """
    ipm_base = _ipm_valor(anio_curso, 2)
    primer_dia_mes_pago = fecha_pago.replace(day=1)
    mes_anterior = primer_dia_mes_pago - datetime.timedelta(days=1)
    ipm_anterior = _ipm_valor(mes_anterior.year, mes_anterior.month)
    if not ipm_base or not ipm_anterior:
        return None
    return ((ipm_anterior / ipm_base) - Decimal("1")) * CIEN


def _tim_factor(anio: int, mes: int) -> Decimal | None:
    """
    TIM del mes. Si ese mes no esta cargado todavia, usa la ultima tasa
    vigente conocida (la mas reciente <= ese mes). Asi un atraso que llega
    hasta un mes sin tasa publicada sigue acumulando con la ultima tasa.
    """
    cache = _tim_cache()
    exacto = cache.get((anio, mes))
    if exacto is not None:
        return exacto
    orden: list[tuple[int, int]] = _CACHE["tim_orden"]  # type: ignore[assignment]
    ultima: Decimal | None = None
    objetivo = (anio, mes)
    for clave in orden:
        if clave <= objetivo:
            ultima = cache[clave]
        else:
            break
    return ultima


# ---------------------------------------------------------------------------
# Vencimiento
# ---------------------------------------------------------------------------


def _ultimo_dia_mes(anio: int, mes: int) -> datetime.date:
    ultimo = calendar.monthrange(anio, mes)[1]
    return datetime.date(anio, mes, ultimo)


def vencimiento_trimestre(anio: int, trimestre: int) -> datetime.date:
    """
    Vencimiento estandar del Impuesto Predial: ultimo dia del mes de cada
    trimestre (Feb / May / Ago / Nov). Aproximamos "ultimo dia habil" con el
    ultimo dia calendario (suficiente para el calculo de interes; se puede
    sobreescribir pasando fecha_vencimiento explicita).
    """
    mes = MES_VENCIMIENTO_TRIMESTRE.get(trimestre)
    if not mes:
        raise ValueError(f"Trimestre invalido: {trimestre!r} (esperado 1-4).")
    return _ultimo_dia_mes(anio, mes)


# ---------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------


@dataclass
class Penalidades:
    base: Decimal
    anio_deuda: int
    trimestre: int
    reajuste: Decimal
    interes: Decimal
    dias_atraso: int
    fecha_vencimiento: datetime.date
    fecha_pago: datetime.date
    metodo_reajuste: str  # "tabla" | "exento_q1" | "sin_factor"
    # Valores SIN redondear (precision completa). Se usan para sumar varias
    # cuotas y redondear UNA sola vez al final, evitando el sesgo de redondear
    # cada cuota por separado. `reajuste`/`interes` son la version a 2 decimales.
    reajuste_raw: Decimal = Decimal("0")
    interes_raw: Decimal = Decimal("0")

    @property
    def total_penalidades(self) -> Decimal:
        return _q(self.reajuste + self.interes)

    @property
    def total_con_penalidades(self) -> Decimal:
        return _q(self.base + self.reajuste + self.interes)

    def to_dict(self) -> dict:
        return {
            "base": float(self.base),
            "anio_deuda": self.anio_deuda,
            "trimestre": self.trimestre,
            "reajuste": float(self.reajuste),
            "interes": float(self.interes),
            "dias_atraso": self.dias_atraso,
            "fecha_vencimiento": self.fecha_vencimiento.isoformat(),
            "fecha_pago": self.fecha_pago.isoformat(),
            "metodo_reajuste": self.metodo_reajuste,
            "total_penalidades": float(self.total_penalidades),
            "total_con_penalidades": float(self.total_con_penalidades),
        }


# ---------------------------------------------------------------------------
# Calculo de reajuste
# ---------------------------------------------------------------------------


def _calcular_reajuste(
    base: Decimal,
    anio_deuda: int,
    trimestre: int,
) -> tuple[Decimal, str]:
    """
    Reajuste de UNA cuota leido de TABREAJUSTE (valor congelado por SIAP).
    Aplica a todos los años por igual; ver docstring del modulo.
    """
    # Regla legal: la 1ra cuota nunca se reajusta.
    if trimestre == 1:
        return Decimal("0.00"), "exento_q1"

    fact = _reajuste_factor(anio_deuda, trimestre)
    if fact is None:
        # Sin fila: el trimestre aun no fue congelado (no vencido) o sin dato.
        return Decimal("0.00"), "sin_factor"

    # ReajFact esta en porcentaje -> dividir entre 100.
    return (base * fact / CIEN), "tabla"


# ---------------------------------------------------------------------------
# Calculo de interes moratorio
# ---------------------------------------------------------------------------


def _calcular_interes(
    base: Decimal,
    fecha_vencimiento: datetime.date,
    fecha_pago: datetime.date,
) -> tuple[Decimal, int]:
    """
    Interes acumulado mes a mes desde el dia siguiente al vencimiento hasta
    la fecha de pago (inclusive). Devuelve (interes, dias_atraso).
    """
    inicio = fecha_vencimiento + datetime.timedelta(days=1)
    if fecha_pago < inicio:
        return Decimal("0.00"), 0

    dias_atraso = (fecha_pago - fecha_vencimiento).days  # = dias desde 'inicio'

    factor_acumulado = Decimal("0")
    tramo_inicio = inicio
    anio, mes = inicio.year, inicio.month

    # Recorremos mes por mes acumulando (tasa_diaria_mes / 100) * dias_en_mes
    while (anio, mes) <= (fecha_pago.year, fecha_pago.month):
        fin_mes = _ultimo_dia_mes(anio, mes)
        tramo_fin = min(fin_mes, fecha_pago)
        dias_tramo = (tramo_fin - tramo_inicio).days + 1

        tim = _tim_factor(anio, mes) or Decimal("0")
        tim_diaria = tim / TREINTA
        factor_acumulado += (tim_diaria / CIEN) * Decimal(dias_tramo)

        # avanzar al primer dia del mes siguiente
        if mes == 12:
            anio, mes = anio + 1, 1
        else:
            mes += 1
        tramo_inicio = datetime.date(anio, mes, 1)

    return (base * factor_acumulado), dias_atraso


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------


def calcular_penalidades_tributarias(
    deuda_base,
    anio_deuda: int,
    trimestre: int,
    fecha_pago: datetime.date,
    *,
    fecha_vencimiento: datetime.date | None = None,
    anio_en_curso: int | None = None,
) -> Penalidades:
    """
    Calcula reajuste + interes moratorio de UNA cuota trimestral.

    Args:
        deuda_base: importe base (insoluto) de la cuota del trimestre.
        anio_deuda: año al que pertenece la deuda.
        trimestre: 1..4.
        fecha_pago: fecha en que se paga / consulta (hoy, normalmente).
        fecha_vencimiento: opcional; si no se pasa se deriva del calendario
            estandar (ultimo dia de Feb/May/Ago/Nov segun trimestre).
        anio_en_curso: opcional; por defecto fecha_pago.year. Determina si el
            reajuste es estatico (años cerrados) o dinamico por IPM (año actual).

    Returns:
        Penalidades con reajuste, interes, dias_atraso y totales (2 decimales).
    """
    base = _d(deuda_base)
    if anio_en_curso is None:
        anio_en_curso = fecha_pago.year
    if fecha_vencimiento is None:
        fecha_vencimiento = vencimiento_trimestre(anio_deuda, trimestre)

    reajuste_raw, metodo = _calcular_reajuste(base, anio_deuda, trimestre)

    # Interes moratorio SOLO para años anteriores al año en curso. El año en
    # curso lleva unicamente reajuste (verificado en reportes: interes año
    # actual = 0.00).
    if anio_deuda < anio_en_curso:
        interes_raw, dias = _calcular_interes(base, fecha_vencimiento, fecha_pago)
    else:
        interes_raw, dias = Decimal("0.00"), 0

    return Penalidades(
        base=_q(base),
        anio_deuda=anio_deuda,
        trimestre=trimestre,
        reajuste=_q(reajuste_raw),
        interes=_q(interes_raw),
        dias_atraso=dias,
        fecha_vencimiento=fecha_vencimiento,
        fecha_pago=fecha_pago,
        metodo_reajuste=metodo,
        reajuste_raw=Decimal(reajuste_raw),
        interes_raw=Decimal(interes_raw),
    )


@dataclass
class PenalidadesAnuales:
    anio_deuda: int
    base_anual: Decimal
    reajuste: Decimal
    interes: Decimal
    total_con_penalidades: Decimal
    cuotas: list[Penalidades]

    def to_dict(self) -> dict:
        return {
            "anio_deuda": self.anio_deuda,
            "base_anual": float(self.base_anual),
            "reajuste": float(self.reajuste),
            "interes": float(self.interes),
            "total_con_penalidades": float(self.total_con_penalidades),
            "cuotas": [c.to_dict() for c in self.cuotas],
        }


def calcular_penalidades_anuales(
    base_anual,
    anio_deuda: int,
    fecha_pago: datetime.date,
    *,
    anio_en_curso: int | None = None,
) -> PenalidadesAnuales:
    """
    Calcula reajuste + interes de una deuda ANUAL del Impuesto Predial,
    repartiendola en 4 cuotas trimestrales (base_anual / 4) y sumando las
    penalidades de cada trimestre.

    Es el helper que se integra con `listar_deudas_detalle`, que maneja
    importes anuales (IpaImpAutoCal).
    """
    base_anual_d = _d(base_anual)
    cuota = base_anual_d / Decimal("4")

    cuotas: list[Penalidades] = []
    for trimestre in (1, 2, 3, 4):
        cuotas.append(
            calcular_penalidades_tributarias(
                cuota,
                anio_deuda,
                trimestre,
                fecha_pago,
                anio_en_curso=anio_en_curso,
            )
        )

    # Sumamos los valores SIN redondear y redondeamos UNA sola vez. Asi no
    # arrastramos el sesgo de redondear cada cuota por separado (lo correcto
    # cuando un total anual se compone de 4 cuotas).
    reajuste_total = _q(sum((c.reajuste_raw for c in cuotas), Decimal("0")))
    interes_total = _q(sum((c.interes_raw for c in cuotas), Decimal("0")))
    total = _q(base_anual_d + reajuste_total + interes_total)

    return PenalidadesAnuales(
        anio_deuda=anio_deuda,
        base_anual=_q(base_anual_d),
        reajuste=reajuste_total,
        interes=interes_total,
        total_con_penalidades=total,
        cuotas=cuotas,
    )
