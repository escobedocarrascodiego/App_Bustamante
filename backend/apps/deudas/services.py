"""
Consulta de deuda real contra la base de datos muni_db (MuniJLByR).

Replica exacta del `comprobar_deuda_api` del codigo legado (Escudo Maestro V3 +
Anti-Decimales + Anti-Fraccionamientos). SQL crudo con NOLOCK: solo lectura,
no toca nada en produccion.
"""
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import TypedDict

from django.db import connections
from django.utils import timezone

from apps.deudas.penalidades import calcular_penalidades_anuales


class EstadoBustaCard:
    NO_PROPIETARIO = "NO_PROPIETARIO"
    TIENE_DEUDA = "TIENE_DEUDA"
    AL_DIA = "AL_DIA"
    ERROR = "ERROR"


class DeudaMuniResult(TypedDict):
    cntrcod: int | None
    nombre: str | None
    estado_busta_card: str
    tiene_deuda: bool
    deuda_total: float
    mensaje: str
    anio: int


class DeudaDetalleItem(TypedDict):
    origen: str
    concepto: str
    sub_rubro: str | None
    anio: int | None
    mes: int | None
    predio_cod: str | None
    predio_direccion: str | None   # ej. "DANIEL ALCIDES CARRION - MZ L / LOTE 03"
    prd_con_cod: int | None        # 1=PU, 4=SC, etc (PREDIOCOND.PrdConCod)
    condicion_nombre: str | None   # ej. "PROPIETARIO UNICO"
    importe_original: float
    cargos_reajuste: float
    pagado: float
    saldo_pendiente: float


# Cache simple de PREDIOCOND (1 query por proceso, no cambia en runtime).
_PREDIOCOND_CACHE: dict[int, str] | None = None


def _cargar_prediocond() -> dict[int, str]:
    """Devuelve {PrdConCod: PrdConDes} desde PREDIOCOND."""
    global _PREDIOCOND_CACHE
    if _PREDIOCOND_CACHE is not None:
        return _PREDIOCOND_CACHE
    out: dict[int, str] = {}
    try:
        with connections["muni_db"].cursor() as cursor:
            cursor.execute(
                "SELECT PrdConCod, PrdConDes FROM PREDIOCOND WITH (NOLOCK) "
                "WHERE PrdConAnu = ' '"
            )
            for cod, des in cursor.fetchall():
                out[int(cod)] = (des or "").strip()
    except Exception as exc:  # pragma: no cover
        print(f"[prediocond] error: {exc!r}")
        return {}
    _PREDIOCOND_CACHE = out
    return out


def _cargar_direcciones_predios(predios_cods: set[int]) -> dict[int, str]:
    """
    Devuelve `{PrdCod: 'ZONA - MZ X / LOTE Y'}` para los predios pedidos.

    Construye la direccion legible juntando ZONAS.ZonaDes + PREDIO.PrdManzana
    + PREDIO.PrdLote. Si el predio no tiene manzana/lote (caso de predios
    rusticos o sin numerar), devuelve solo la zona.

    Una sola query con un IN (...) para no hacer N+1 por cada item de deuda.
    """
    if not predios_cods:
        return {}

    placeholders = ",".join(["%s"] * len(predios_cods))
    sql = f"""
        SELECT
            p.PrdCod,
            LTRIM(RTRIM(ISNULL(z.ZonaDes, ''))) AS Zona,
            LTRIM(RTRIM(ISNULL(p.PrdManzana, ''))) AS Manzana,
            LTRIM(RTRIM(ISNULL(p.PrdLote, ''))) AS Lote
        FROM PREDIO p WITH (NOLOCK)
        LEFT JOIN ZONAS z WITH (NOLOCK) ON z.ZonaCod = p.ZonaCod
        WHERE p.PrdCod IN ({placeholders})
    """
    direcciones: dict[int, str] = {}
    try:
        with connections["muni_db"].cursor() as cursor:
            cursor.execute(sql, list(predios_cods))
            for row in cursor.fetchall():
                prd_cod, zona, mz, lote = row
                if prd_cod is None:
                    continue
                partes: list[str] = []
                if zona:
                    partes.append(zona)
                if mz and lote:
                    partes.append(f"MZ {mz} / LOTE {lote}")
                elif mz:
                    partes.append(f"MZ {mz}")
                elif lote:
                    partes.append(f"LOTE {lote}")
                direcciones[int(prd_cod)] = " - ".join(partes) if partes else ""
    except Exception as exc:  # pragma: no cover
        print(f"[predios] error cargando direcciones: {exc!r}")
        return {}
    return direcciones


def buscar_contribuyentes(term: str, limite: int = 50) -> list[dict]:
    """
    Busca contribuyentes en CONTRIBUYENTES (muni_db) por:
      - DNI / numero de documento (LIKE por prefijo)
      - Codigo de contribuyente (CntrCod exacto)
      - Nombres / apellidos (cada palabra debe aparecer en CntrNom)

    Usado por el modulo de ventanilla (/genera_bustacard) para que un
    administrador ubique al contribuyente. Parametrizado (sin inyeccion),
    NOLOCK, limitado a `limite` filas.

    Devuelve [{cntrcod, dni, nombre, direccion}].
    """
    term = (term or "").strip()
    if len(term) < 2:
        return []

    base = (
        "SELECT TOP (%s) CntrCod, LTRIM(RTRIM(CntrNumDoc)) AS Dni, "
        "LTRIM(RTRIM(CntrNom)) AS Nombre, "
        "LTRIM(RTRIM(ISNULL(CntrDirecLar, CntrDirec))) AS Direccion "
        "FROM CONTRIBUYENTES WITH (NOLOCK) WHERE CntrAnu = ' ' "
    )

    solo_digitos = term.replace(" ", "").isdigit()
    params: list = [limite]

    if solo_digitos:
        # DNI por prefijo o CntrCod exacto.
        num = term.replace(" ", "")
        base += "AND (LTRIM(RTRIM(CntrNumDoc)) LIKE %s OR CAST(CntrCod AS VARCHAR(20)) = %s) "
        params += [f"{num}%", num]
    else:
        # Cada palabra del nombre debe aparecer en CntrNom.
        palabras = [p for p in term.upper().split() if p]
        for palabra in palabras:
            base += "AND UPPER(CntrNom) LIKE %s "
            params.append(f"%{palabra}%")

    base += "ORDER BY CntrNom"

    resultado: list[dict] = []
    try:
        with connections["muni_db"].cursor() as cursor:
            cursor.execute(base, params)
            for cntrcod, dni, nombre, direccion in cursor.fetchall():
                resultado.append({
                    "cntrcod": int(cntrcod),
                    "dni": (dni or "").strip(),
                    "nombre": (nombre or "").strip(),
                    "direccion": (direccion or "").strip(),
                })
    except Exception as exc:  # pragma: no cover
        print(f"[buscar-contribuyentes] error term={term!r}: {exc!r}")
        return []
    return resultado


def obtener_contribuyente(cntrcod: int) -> dict | None:
    """Datos basicos de un contribuyente por CntrCod (para la BustaCard)."""
    if not cntrcod:
        return None
    sql = (
        "SELECT CntrCod, LTRIM(RTRIM(CntrNumDoc)) AS Dni, "
        "LTRIM(RTRIM(CntrNom)) AS Nombre, "
        "LTRIM(RTRIM(ISNULL(CntrDirecLar, CntrDirec))) AS Direccion "
        "FROM CONTRIBUYENTES WITH (NOLOCK) WHERE CntrCod = %s"
    )
    try:
        with connections["muni_db"].cursor() as cursor:
            cursor.execute(sql, [int(cntrcod)])
            row = cursor.fetchone()
    except Exception as exc:  # pragma: no cover
        print(f"[obtener-contribuyente] error cntrcod={cntrcod}: {exc!r}")
        return None
    if not row:
        return None
    return {
        "cntrcod": int(row[0]),
        "dni": (row[1] or "").strip(),
        "nombre": (row[2] or "").strip(),
        "direccion": (row[3] or "").strip(),
    }


def listar_condiciones_por_dni(dni: str) -> list[dict]:
    """
    Devuelve TODOS los CntrCod que tiene un DNI en CONTRIBUYENTES, junto con
    el nombre de cada condicion (Propietario Unico, Sociedad Conyugal, etc).

    Un mismo DNI puede aparecer en N filas porque la persona tiene varios
    "roles" tributarios — cada rol tiene su propia deuda. Antes resolviamos
    solo el primer match (TOP 1) y perdiamos el resto.
    """
    if not dni:
        return []
    sql = (
        "SELECT CntrCod, CntrNom FROM CONTRIBUYENTES WITH (NOLOCK) "
        "WHERE LTRIM(RTRIM(CntrNumDoc)) = %s ORDER BY CntrCod"
    )
    try:
        with connections["muni_db"].cursor() as cursor:
            cursor.execute(sql, [str(dni).strip()])
            rows = cursor.fetchall()
    except Exception as exc:  # pragma: no cover
        print(f"[condiciones] error resolviendo DNI {dni}: {exc!r}")
        return []
    resultado: list[dict] = []
    for cntrcod, nombre in rows:
        if cntrcod is None:
            continue
        resultado.append({
            "cntrcod": int(cntrcod),
            "nombre": (nombre or "").strip(),
        })
    print(
        f"[condiciones] DNI {dni!r} -> {len(resultado)} fila(s) en "
        f"CONTRIBUYENTES: {[(c['cntrcod'], c['nombre']) for c in resultado]}"
    )
    return resultado


def resolver_cntrcod_por_dni(dni: str) -> int | None:
    """Compat: devuelve el primer CntrCod del DNI (o None)."""
    cs = listar_condiciones_por_dni(dni)
    return cs[0]["cntrcod"] if cs else None


def cntrcod_pertenece_a_dni(cntrcod: int, dni: str) -> bool:
    """Verifica que un CntrCod este registrado contra el DNI dado."""
    if not cntrcod or not dni:
        return False
    return any(c["cntrcod"] == int(cntrcod) for c in listar_condiciones_por_dni(dni))


def obtener_cntrcod_usuario(user) -> int | None:
    """Devuelve el CntrCod del usuario, resolviendo por DNI si hace falta."""
    cntrcod = getattr(user, "cntr_cod", None)
    if cntrcod:
        return int(cntrcod)
    dni = getattr(user, "dni", None)
    return resolver_cntrcod_por_dni(dni) if dni else None


_QUERY_DETALLE = """
;WITH MovimientosCtaCte AS (
    SELECT
        CtCtCod,
        SUM(CASE WHEN TranMovDet = '+' THEN CtCtDImpor ELSE 0 END) AS Cargos,
        SUM(CASE WHEN TranMovDet = '-' THEN CtCtDImpor ELSE 0 END) AS Pagos
    FROM CTACTEDET WITH (NOLOCK)
    WHERE CtCtDFlgAnu = ' '
    GROUP BY CtCtCod
),
DeudaCtaCte AS (
    SELECT
        c.CntrCod,
        c.CtCtConCod          AS PrdConCod,
        c.RubroCod,
        c.SRubCod,
        c.CtCtAno             AS Anio,
        c.CtCtMes             AS Mes,
        c.IpaCod,
        c.CtCtImpor           AS ImporteOriginal,
        ISNULL(m.Cargos, 0)   AS CargosExtra,
        ISNULL(m.Pagos, 0)    AS Pagado,
        -- "Deuda con Amnistia": SIAP perdona multa + interes acumulados,
        -- solo cobra el principal pendiente + formularios. CargosExtra
        -- (TranMovDet='+') incluye multa/interes que se condonan, asi que
        -- no lo sumamos al total. Mantenemos el campo informativo aparte.
        -- Clamp en 0 por si Pagos > ImporteOriginal (sobre-pago historico).
        CASE
            WHEN c.CtCtImpor - ISNULL(m.Pagos, 0) > 0
            THEN c.CtCtImpor - ISNULL(m.Pagos, 0)
            ELSE 0
        END AS SaldoPendiente
    FROM CTACTE c WITH (NOLOCK)
    LEFT JOIN MovimientosCtaCte m ON c.CtCtCod = m.CtCtCod
    WHERE c.CntrCod = %s
      AND c.CtCtFlgAnu = ' '
),
PrediosTitular AS (
    SELECT
        CntrCod,
        PrdConCod,
        IpaCod,
        IpaAno                AS Anio,
        IpaValAuto,
        IpaImpAutoCal         AS PredialCalculado,
        IpaImpARBCal          AS ArbitrioRBCalc,
        IpaImpABVCal          AS ArbitrioBVCalc,
        IpaImpAPJCal          AS ArbitrioPJCalc,
        IpaSerImpCal          AS SerenazgoCalc,
        IpaFlgPagado          AS FlgPagadoPredial,
        IpaFlgPagadoArb       AS FlgPagadoArb,
        IpaSerGeneFlg         AS FlgSerGenerado
    FROM IMPPREANU WITH (NOLOCK)
    WHERE CntrCod   = %s
      AND IpaFlgAnu = ' '
),
-- Predios donde el contribuyente es CO-PROPIETARIO (coop. varios, sociedad
-- conyugal con principal en el conyuge, sucesion, etc). Los importes ya
-- vienen pro-rateados en IpaCntrImpu*Cal segun su porcentaje.
PrediosCoopVarios AS (
    SELECT
        ipc.IpaCntrCod                       AS CntrCod,
        ipc.IpaPrdConCod                     AS PrdConCod,
        ipc.IpaCod,
        ipc.IpaAno                           AS Anio,
        ISNULL(ipc.IpaCntrImpuCal, 0)        AS PredialCalculado,
        ISNULL(ipc.IpaCntrRBCal, 0)          AS ArbitrioRBCalc,
        ISNULL(ipc.IpaCntrBVCal, 0)          AS ArbitrioBVCalc,
        ISNULL(ipc.IpaCntrPJCal, 0)          AS ArbitrioPJCalc,
        ISNULL(ipc.IpaCntrSereCal, 0)        AS SerenazgoCalc,
        ISNULL(ipc.IpaGeneFlg, 0)            AS FlgGenPredial,
        ISNULL(ipc.IpaGeneArbFlg, 0)         AS FlgGenArb,
        ISNULL(ipc.IpaGeneSereFlg, 0)        AS FlgGenSer
    FROM IMPPREANUCNTR ipc WITH (NOLOCK)
    WHERE ipc.IpaCntrCod = %s
)

-- 1) DEUDA REGISTRADA EN CTACTE
SELECT
    'DEUDA REGISTRADA' AS Origen,
    CASE d.RubroCod
        WHEN 1 THEN '1. Impuesto Predial'
        WHEN 2 THEN '2. Arbitrios (Limpieza/Parques/Serenazgo antiguo)'
        WHEN 8 THEN '3. Serenazgo'
        ELSE '4. Otros (Rubro ' + CAST(d.RubroCod AS VARCHAR) + ')'
    END                       AS Concepto,
    CAST(d.SRubCod AS VARCHAR(50))  AS SubRubro,
    d.Anio,
    d.Mes,
    CAST(d.IpaCod AS VARCHAR(50))    AS PredioCod,
    CAST(SUM(d.ImporteOriginal) AS FLOAT) AS ImporteOriginal,
    CAST(SUM(d.CargosExtra)     AS FLOAT) AS CargosReajuste,
    CAST(SUM(d.Pagado)          AS FLOAT) AS Pagado,
    CAST(SUM(d.SaldoPendiente)  AS FLOAT) AS SaldoPendiente,
    d.PrdConCod                          AS PrdConCod
FROM DeudaCtaCte d
WHERE d.RubroCod IN (1, 2, 8)
GROUP BY d.RubroCod, d.SRubCod, d.Anio, d.Mes, d.IpaCod, d.PrdConCod
HAVING SUM(d.SaldoPendiente) > 0.01

UNION ALL

-- 2) PREDIAL CALCULADO PERO NO REGISTRADO EN CTACTE
--    OJO: filtramos por IpaFlgPagado = 0 igual que en arbitrios. Sin esto
--    se contaban años antiguos ya pagados como si fueran deuda viva
--    (caso real: contribuyente con 9 años en IMPPREANU pero solo 2 pendientes,
--    estabamos sumando los 9 e inflando el total ~2x).
--
--    BUG HISTORICO: antes filtrabamos ademas con NOT EXISTS contra CTACTE
--    rubro=1, lo que excluia el predial de IMPPREANU si SIAP tenia algun
--    cargo administrativo del año (formulario S/10, recargos chicos)
--    aunque el predial completo NO estuviera generado. Resultado: para un
--    contribuyente con cargos pagados de S/10 en 2019/2020/2021, el predial
--    completo S/863+S/885+S/899 desaparecia. Caso real: DNI 02008230,
--    deuda real 8532.59 vs reportada 5763.64 (faltaba 2768.95).
--
--    Ahora confiamos en IpaFlgPagado: si dice 0, el predial NO esta generado
--    completamente y es deuda viva, sin importar que haya cargos chicos en
--    CTACTE del mismo año. Cuando se genera de verdad, IpaFlgPagado pasa a 1.
SELECT
    'PREDIAL NO GENERADO (TITULAR)' AS Origen,
    '1. Impuesto Predial'      AS Concepto,
    NULL                       AS SubRubro,
    p.Anio,
    NULL                       AS Mes,
    CAST(p.IpaCod AS VARCHAR(50)) AS PredioCod,
    CAST(p.PredialCalculado AS FLOAT) AS ImporteOriginal,
    0.0                        AS CargosReajuste,
    0.0                        AS Pagado,
    CAST(p.PredialCalculado AS FLOAT) AS SaldoPendiente,
    p.PrdConCod                       AS PrdConCod
FROM PrediosTitular p
WHERE p.PredialCalculado > 0
  AND p.FlgPagadoPredial = 0

UNION ALL

-- 3) SERENAZGO CALCULADO PERO NO GENERADO
SELECT
    'SERENAZGO NO GENERADO' AS Origen,
    '3. Serenazgo'          AS Concepto,
    NULL                    AS SubRubro,
    p.Anio,
    NULL                    AS Mes,
    CAST(p.IpaCod AS VARCHAR(50)) AS PredioCod,
    CAST(p.SerenazgoCalc AS FLOAT) AS ImporteOriginal,
    0.0, 0.0,
    CAST(p.SerenazgoCalc AS FLOAT) AS SaldoPendiente,
    p.PrdConCod                    AS PrdConCod
FROM PrediosTitular p
WHERE p.FlgSerGenerado = 0
  AND p.SerenazgoCalc  > 0

UNION ALL

-- 4) ARBITRIOS CALCULADOS PERO NO GENERADOS
--    Mismo motivo que SELECT 2: quitamos el NOT EXISTS contra CTACTE Rubro=2
--    porque cargos chicos pagados (cuotas individuales menores) lo activaban
--    indebidamente y dejaban fuera arbitrios completos no generados.
SELECT
    'ARBITRIOS NO GENERADOS' AS Origen,
    '2. Arbitrios'          AS Concepto,
    NULL                    AS SubRubro,
    p.Anio,
    NULL                    AS Mes,
    CAST(p.IpaCod AS VARCHAR(50)) AS PredioCod,
    CAST((p.ArbitrioRBCalc + p.ArbitrioBVCalc + p.ArbitrioPJCalc) AS FLOAT) AS ImporteOriginal,
    0.0, 0.0,
    CAST((p.ArbitrioRBCalc + p.ArbitrioBVCalc + p.ArbitrioPJCalc) AS FLOAT) AS SaldoPendiente,
    p.PrdConCod                    AS PrdConCod
FROM PrediosTitular p
WHERE p.FlgPagadoArb = 0
  AND (p.ArbitrioRBCalc + p.ArbitrioBVCalc + p.ArbitrioPJCalc) > 0

UNION ALL

-- 5) PREDIAL CO-PROPIETARIO NO GENERADO (IMPPREANUCNTR)
--    Sin NOT EXISTS por las mismas razones que SELECT 2: confiamos en
--    IpaGeneFlg de IMPPREANUCNTR como source of truth.
SELECT
    'PREDIAL NO GENERADO (CO-PROP)' AS Origen,
    '1. Impuesto Predial'      AS Concepto,
    NULL                       AS SubRubro,
    p.Anio,
    NULL                       AS Mes,
    CAST(p.IpaCod AS VARCHAR(50)) AS PredioCod,
    CAST(p.PredialCalculado AS FLOAT) AS ImporteOriginal,
    0.0, 0.0,
    CAST(p.PredialCalculado AS FLOAT) AS SaldoPendiente,
    p.PrdConCod                       AS PrdConCod
FROM PrediosCoopVarios p
WHERE p.PredialCalculado > 0
  AND p.FlgGenPredial = 0

UNION ALL

-- 6) SERENAZGO CO-PROPIETARIO NO GENERADO
SELECT
    'SERENAZGO NO GENERADO (CO-PROP)' AS Origen,
    '3. Serenazgo'             AS Concepto,
    NULL                       AS SubRubro,
    p.Anio,
    NULL                       AS Mes,
    CAST(p.IpaCod AS VARCHAR(50)) AS PredioCod,
    CAST(p.SerenazgoCalc AS FLOAT) AS ImporteOriginal,
    0.0, 0.0,
    CAST(p.SerenazgoCalc AS FLOAT) AS SaldoPendiente,
    p.PrdConCod                    AS PrdConCod
FROM PrediosCoopVarios p
WHERE p.FlgGenSer = 0
  AND p.SerenazgoCalc > 0

UNION ALL

-- 7) ARBITRIOS CO-PROPIETARIO NO GENERADOS (RB+BV+PJ ya pro-rateados)
--    Sin NOT EXISTS: confiamos en IpaGeneArbFlg de IMPPREANUCNTR.
SELECT
    'ARBITRIOS NO GENERADOS (CO-PROP)' AS Origen,
    '2. Arbitrios'             AS Concepto,
    NULL                       AS SubRubro,
    p.Anio,
    NULL                       AS Mes,
    CAST(p.IpaCod AS VARCHAR(50)) AS PredioCod,
    CAST((p.ArbitrioRBCalc + p.ArbitrioBVCalc + p.ArbitrioPJCalc) AS FLOAT) AS ImporteOriginal,
    0.0, 0.0,
    CAST((p.ArbitrioRBCalc + p.ArbitrioBVCalc + p.ArbitrioPJCalc) AS FLOAT) AS SaldoPendiente,
    p.PrdConCod                    AS PrdConCod
FROM PrediosCoopVarios p
WHERE p.FlgGenArb = 0
  AND (p.ArbitrioRBCalc + p.ArbitrioBVCalc + p.ArbitrioPJCalc) > 0

ORDER BY Concepto, Anio, Mes, PredioCod;
"""


# Cargo SIAP por "formulario predial" cuando el predial aun no fue generado.
# Formula confirmada con PDFs reales:
#   - 1 predio  -> S/10
#   - 2 predios -> S/15
#   - 5 predios -> S/30
# Patron general: 5 * (n_predios + 1)
#
# Se aplica POR (condicion, año) — un contribuyente con PU + SC paga formulario
# separado para cada condicion.
def _cargo_formulario(n_predios: int) -> float:
    """Cargo de formulario para predial NO generado segun cantidad de predios."""
    if n_predios <= 0:
        return 0.0
    return 5.0 * (n_predios + 1)


def listar_deudas_detalle(cntrcod: int) -> list[DeudaDetalleItem]:
    """
    Desglose completo de deuda del contribuyente contra MuniJLByR.
    Fuente: CTACTE + CTACTEDET + IMPPREANU. Sin tabla local.
      1) DEUDA REGISTRADA (CTACTE, rubros 1/2/8)
      2) PREDIAL NO GENERADO TITULAR (IMPPREANU sin fila en CTACTE)
      3) SERENAZGO NO GENERADO (IpaSerGeneFlg = 0)
      4) ARBITRIOS NO GENERADOS (IpaFlgPagadoArb = 0, suma RB+BV+PJ)
      5) FORMULARIO PREDIAL: cargo administrativo por cada predio no
         generado (CARGO_FORMULARIO_POR_PREDIO).

    Esta es la UNICA fuente de verdad para "deuda total" — comprobar_deuda
    (la validacion de la BustaCard) tambien la consume para decidir si
    hay deuda o no. Asi nunca hay diferencia entre Mis Deudas y Tarjeta.
    """
    detalle: list[DeudaDetalleItem] = []
    try:
        with connections["muni_db"].cursor() as cursor:
            # 3 binds: CTACTE.CntrCod, IMPPREANU.CntrCod, IMPPREANUCNTR.IpaCntrCod
            cursor.execute(_QUERY_DETALLE, [cntrcod, cntrcod, cntrcod])
            rows = cursor.fetchall()
    except Exception as exc:  # pragma: no cover
        print(f"[detalle-deuda] error: {exc!r}")
        return []

    nombres_cond = _cargar_prediocond()

    for r in rows:
        (origen, concepto, sub_rubro, anio, mes, predio_cod,
         importe, cargos, pagado, saldo, prd_con_cod) = r
        prd_con_cod_int = int(prd_con_cod) if prd_con_cod is not None else None
        detalle.append({
            "origen": origen or "",
            "concepto": concepto or "",
            "sub_rubro": (str(sub_rubro).strip() if sub_rubro not in (None, " ", "") else None),
            "anio": int(anio) if anio is not None else None,
            "mes": int(mes) if mes is not None else None,
            "predio_cod": str(predio_cod) if predio_cod is not None else None,
            "predio_direccion": None,  # se completa abajo en una query batch
            "prd_con_cod": prd_con_cod_int,
            "condicion_nombre": (
                nombres_cond.get(prd_con_cod_int)
                if prd_con_cod_int is not None
                else None
            ),
            "importe_original": float(importe or 0),
            "cargos_reajuste": float(cargos or 0),
            "pagado": float(pagado or 0),
            "saldo_pendiente": float(saldo or 0),
        })

    # ----------------------------------------------------------------------
    # CAPTURAR predios pendientes ANTES del reemplazo CTACTE para que el
    # calculo de formulario refleje la cantidad real de predios por año.
    # ----------------------------------------------------------------------
    predios_pendientes_por_cond_anio: dict[tuple[int, int], set[str]] = {}
    nombres_cond_por_cod: dict[int, str] = {}
    for d in detalle:
        if d["origen"] not in (
            "PREDIAL NO GENERADO (TITULAR)",
            "PREDIAL NO GENERADO (CO-PROP)",
        ):
            continue
        cond = d["prd_con_cod"]
        anio = d["anio"]
        predio = d["predio_cod"]
        if cond is None or anio is None:
            continue
        key = (int(cond), int(anio))
        predios_pendientes_por_cond_anio.setdefault(key, set()).add(
            predio or f"_sin_predio_{id(d)}"
        )
        if d.get("condicion_nombre"):
            nombres_cond_por_cod[int(cond)] = d["condicion_nombre"]

    # ----------------------------------------------------------------------
    # POST-PROCESO: estimar predial anual de años no generados usando CTACTE
    # ----------------------------------------------------------------------
    # Para Sociedad Conyugal (y similares con multiples predios) SIAP
    # consolida la cuota anual en UN solo "predio principal" por año (el
    # principal varia: en 2023 fue 38626, en 2025 fue 38630). Los demas
    # predios SC quedan con FlgPagado=1 aunque IpaImpAutoCal sea pequeño
    # ("ya estan cobrados via el principal").
    #
    # Cuando un año no tiene cuotas generadas (ej. 2024 y 2026), nuestra
    # rama PREDIAL NO GENERADO (TITULAR) suma IpaImpAutoCal de todos los
    # predios y nos da un valor MUY POR DEBAJO del real (~622 vs ~1430).
    #
    # Solucion: para cada (PrdConCod) que tenga cuotas CTACTE en algun año,
    # tomamos el ULTIMO año con CTACTE como ESTIMACION para los años sin
    # generar. Reemplazamos los items per-predio por uno solo agregado.
    #
    # Solo aplicamos el reemplazo cuando la estimacion CTACTE supera el
    # 1.5x del sum IMPPREANU para esa condicion+año — asi no rompemos casos
    # como Coopropiedad Varios donde IpaImpAutoCal ya es ~la cuota real.
    UMBRAL_REEMPLAZO = 1.5

    # 1. Agrupar CTACTE annual predial por (cond, anio)
    ctacte_annual_por_cond_anio: dict[tuple[int, int], float] = {}
    for d in detalle:
        if d["origen"] != "DEUDA REGISTRADA":
            continue
        if d["concepto"] != "1. Impuesto Predial":
            continue
        cond = d["prd_con_cod"]
        anio = d["anio"]
        if cond is None or anio is None:
            continue
        key = (int(cond), int(anio))
        ctacte_annual_por_cond_anio[key] = (
            ctacte_annual_por_cond_anio.get(key, 0.0) + float(d["saldo_pendiente"])
        )

    # 2. Para cada cond, encontrar el año mas reciente con CTACTE
    ultima_estimacion_por_cond: dict[int, tuple[int, float]] = {}
    for (cond, anio), total in ctacte_annual_por_cond_anio.items():
        if cond not in ultima_estimacion_por_cond or anio > ultima_estimacion_por_cond[cond][0]:
            ultima_estimacion_por_cond[cond] = (anio, total)

    # 3. Sumar IMPPREANU titular por (cond, anio)
    imp_sum_por_cond_anio: dict[tuple[int, int], float] = {}
    for d in detalle:
        if d["origen"] != "PREDIAL NO GENERADO (TITULAR)":
            continue
        cond = d["prd_con_cod"]
        anio = d["anio"]
        if cond is None or anio is None:
            continue
        key = (int(cond), int(anio))
        imp_sum_por_cond_anio[key] = (
            imp_sum_por_cond_anio.get(key, 0.0) + float(d["saldo_pendiente"])
        )

    # 4. Decidir que (cond, anio) reemplazar
    reemplazos: dict[tuple[int, int], float] = {}
    for (cond, anio), suma_imp in imp_sum_por_cond_anio.items():
        if cond not in ultima_estimacion_por_cond:
            continue
        estimacion = ultima_estimacion_por_cond[cond][1]
        if estimacion > suma_imp * UMBRAL_REEMPLAZO:
            reemplazos[(cond, anio)] = estimacion

    # 5. Reemplazar items: quitar los IMPPREANU titular per-predio para
    # (cond, anio) que vamos a estimar, y agregar uno solo agregado.
    if reemplazos:
        nombres_por_cond = {
            d["prd_con_cod"]: d["condicion_nombre"]
            for d in detalle
            if d["prd_con_cod"] is not None
        }
        nuevo_detalle: list[DeudaDetalleItem] = []
        for d in detalle:
            if d["origen"] == "PREDIAL NO GENERADO (TITULAR)":
                cond = d["prd_con_cod"]
                anio = d["anio"]
                if cond is not None and anio is not None and (int(cond), int(anio)) in reemplazos:
                    continue  # se reemplaza
            nuevo_detalle.append(d)
        for (cond, anio), estimacion in reemplazos.items():
            nuevo_detalle.append({
                "origen": "PREDIAL NO GENERADO (TITULAR)",
                "concepto": "1. Impuesto Predial",
                "sub_rubro": None,
                "anio": anio,
                "mes": None,
                "predio_cod": None,
                "prd_con_cod": cond,
                "condicion_nombre": nombres_por_cond.get(cond),
                "importe_original": float(estimacion),
                "cargos_reajuste": 0.0,
                "pagado": 0.0,
                "saldo_pendiente": float(estimacion),
            })
        detalle = nuevo_detalle
        print(
            f"[detalle-deuda] cntrcod={cntrcod} aplicados "
            f"{len(reemplazos)} reemplazos CTACTE-estimate: {reemplazos}"
        )

    # ----------------------------------------------------------------------
    # PENALIDADES: formulario, reajuste e interes por (condicion, año).
    # Se CALCULAN aqui pero NO se emiten como items separados: se fusionan
    # dentro del item consolidado de "Impuesto Predial" (mas abajo), igual
    # que el reporte SIAP, que muestra el predial por año con su reajuste y
    # formulario en la misma fila.
    # ----------------------------------------------------------------------
    hoy = timezone.localdate()

    # Formulario por (cond, año) segun cantidad de predios pendientes.
    formulario_por_cond_anio: dict[tuple[int, int], float] = {}
    for (cond, anio), predios in predios_pendientes_por_cond_anio.items():
        cargo = _cargo_formulario(len(predios))
        if cargo > 0:
            formulario_por_cond_anio[(cond, anio)] = cargo

    # Base predial pendiente por (cond, año) -> reajuste + interes.
    predial_por_cond_anio: dict[tuple[int, int], float] = {}
    nombres_cond_global: dict[int, str] = {}
    for d in detalle:
        cond = d.get("prd_con_cod")
        if cond is not None and d.get("condicion_nombre"):
            nombres_cond_global[int(cond)] = d["condicion_nombre"]
        if d.get("concepto") != "1. Impuesto Predial":
            continue
        anio = d.get("anio")
        if cond is None or anio is None:
            continue
        key = (int(cond), int(anio))
        predial_por_cond_anio[key] = (
            predial_por_cond_anio.get(key, 0.0)
            + float(d.get("saldo_pendiente") or 0)
        )

    reajuste_por_cond_anio: dict[tuple[int, int], float] = {}
    interes_por_cond_anio: dict[tuple[int, int], float] = {}
    for (cond, anio), base_anual in predial_por_cond_anio.items():
        if base_anual <= 0.01:
            continue
        pen = calcular_penalidades_anuales(base_anual, anio, hoy)
        reajuste_por_cond_anio[(cond, anio)] = float(pen.reajuste)
        interes_por_cond_anio[(cond, anio)] = float(pen.interes)

    # ----------------------------------------------------------------------
    # CONSOLIDAR PREDIAL: un solo item por (cond, año) con
    #   saldo = base + reajuste + formulario   (la "Deuda con Amnistia")
    # Reemplaza a los items base por-predio y evita mostrar formulario y
    # reajuste como filas sueltas. El desglose queda en campos separados
    # (base_predial / reajuste_predial / formulario_predial) para la UI.
    # ----------------------------------------------------------------------
    predial_info: dict[tuple[int, int], dict] = {}
    for d in detalle:
        if d.get("concepto") != "1. Impuesto Predial":
            continue
        cond = d.get("prd_con_cod")
        anio = d.get("anio")
        if cond is None or anio is None:
            continue
        key = (int(cond), int(anio))
        info = predial_info.setdefault(
            key,
            {"base": 0.0, "predios": set(), "condicion_nombre": d.get("condicion_nombre")},
        )
        info["base"] += float(d.get("saldo_pendiente") or 0)
        if d.get("predio_cod"):
            info["predios"].add(d.get("predio_cod"))
        if not info["condicion_nombre"] and d.get("condicion_nombre"):
            info["condicion_nombre"] = d.get("condicion_nombre")

    # Quitar los items base de predial (se reemplazan por el consolidado).
    detalle = [d for d in detalle if d.get("concepto") != "1. Impuesto Predial"]

    for (cond, anio), info in predial_info.items():
        base = float(info["base"])
        if base <= 0.01:
            continue
        reajuste = reajuste_por_cond_anio.get((cond, anio), 0.0)
        formulario = formulario_por_cond_anio.get((cond, anio), 0.0)
        interes = interes_por_cond_anio.get((cond, anio), 0.0)
        saldo = base + reajuste + formulario
        predios = info["predios"]
        predio_unico = next(iter(predios)) if len(predios) == 1 else None
        detalle.append({
            "origen": "IMPUESTO PREDIAL",
            "concepto": "Impuesto Predial",
            "sub_rubro": None,
            "anio": anio,
            "mes": None,
            "predio_cod": predio_unico,
            "predio_direccion": None,  # se completa en el enriquecimiento
            "prd_con_cod": cond,
            "condicion_nombre": info["condicion_nombre"] or nombres_cond_global.get(cond),
            "importe_original": base,
            "cargos_reajuste": 0.0,
            "pagado": 0.0,
            "saldo_pendiente": saldo,            # base + reajuste + formulario
            # Desglose para la UI (no se suma; ya esta dentro de saldo_pendiente):
            "base_predial": base,
            "reajuste_predial": reajuste,
            "formulario_predial": formulario,
            "interes_referencial": interes,      # condonado por amnistia
        })

    # ----------------------------------------------------------------------
    # ENRIQUECER con direccion del predio (ZONAS.ZonaDes + PrdManzana / Lote)
    # ----------------------------------------------------------------------
    # Hacemos UNA sola query batch con todos los predio_cod presentes en
    # los items para evitar N+1. Los items sin predio_cod (FORMULARIO PREDIAL
    # agregado, etc.) quedan con direccion=None.
    predios_cods: set[int] = set()
    for d in detalle:
        pc = d.get("predio_cod")
        if not pc:
            continue
        try:
            predios_cods.add(int(pc))
        except (TypeError, ValueError):
            continue

    direcciones_predios = _cargar_direcciones_predios(predios_cods)
    for d in detalle:
        pc = d.get("predio_cod")
        if not pc:
            continue
        try:
            d["predio_direccion"] = direcciones_predios.get(int(pc))
        except (TypeError, ValueError):
            d["predio_direccion"] = None

    # Resumen para diagnostico
    total_predial = sum(
        d["saldo_pendiente"] for d in detalle if d["origen"] == "IMPUESTO PREDIAL"
    )
    total_reajuste = sum(reajuste_por_cond_anio.values())
    total_form = sum(formulario_por_cond_anio.values())
    total_otros = sum(
        d["saldo_pendiente"] for d in detalle if d["origen"] != "IMPUESTO PREDIAL"
    )
    total = sum(d["saldo_pendiente"] for d in detalle)
    print(
        f"[detalle-deuda] cntrcod={cntrcod} predial(c/penalidad)={total_predial:.2f} "
        f"reajuste={total_reajuste:.2f} formularios={total_form:.2f} "
        f"otros(arb/sere)={total_otros:.2f} total={total:.2f} "
        f"predios_pendientes={ {k: len(v) for k, v in predios_pendientes_por_cond_anio.items()} }"
    )

    # Detalle por item (ordenado por año / origen) para diagnostico fino
    print(f"[detalle-deuda] cntrcod={cntrcod} desglose item por item:")
    items_orden = sorted(
        detalle,
        key=lambda d: (d.get("anio") or 0, d.get("origen") or "", d.get("predio_cod") or ""),
    )
    for d in items_orden:
        print(
            f"  - año={d['anio']} origen={d['origen']!r:<35} "
            f"predio={d['predio_cod']!r:<14} "
            f"importe={d['importe_original']:>9.2f} "
            f"cargos={d['cargos_reajuste']:>9.2f} "
            f"pagado={d['pagado']:>9.2f} "
            f"saldo={d['saldo_pendiente']:>9.2f}"
        )

    return detalle


def _es_propietario_anio(cntrcod: int, anio: int) -> tuple[bool, str | None]:
    """
    Devuelve (es_propietario, nombre). Es propietario si tiene al menos una
    fila en IMPPREANU vigente del ano dado.
    """
    try:
        with connections["muni_db"].cursor() as cursor:
            cursor.execute(
                "SELECT TOP 1 c.CntrNom FROM CONTRIBUYENTES c WITH (NOLOCK) "
                "WHERE c.CntrCod = %s",
                [cntrcod],
            )
            row = cursor.fetchone()
            nombre = (row[0].strip() if row and row[0] else None)

            cursor.execute(
                "SELECT COUNT(1) FROM IMPPREANU WITH (NOLOCK) "
                "WHERE CntrCod = %s AND IpaAno = %s AND IpaFlgAnu = ' '",
                [cntrcod, anio],
            )
            total = cursor.fetchone()[0] or 0
    except Exception as exc:  # pragma: no cover
        print(f"[deuda] _es_propietario_anio error: {exc!r}")
        return (False, None)
    return (int(total) > 0, nombre)


def comprobar_deuda(cntrcod: int) -> DeudaMuniResult:
    """
    Validacion para la BustaCard. UNICA logica:

      1. Resolver si el contribuyente es propietario del año actual.
      2. Calcular deuda total via `listar_deudas_detalle` (misma fuente que
         "Mis Deudas") — esto incluye CTACTE pendientes, predial/arbitrios/
         serenazgo no generados, y el cargo por formulario.
      3. Si total > 0 -> TIENE_DEUDA. Si no es propietario -> NO_PROPIETARIO.
         Solo AL_DIA si propietario y total = 0.

    Endurecimiento: cualquier saldo > 0 (incluso decimales) bloquea la
    emision. Antes la query tenia caminos donde podia perder cargos y
    devolver AL_DIA con deuda real.
    """
    anio_actual = datetime.datetime.now().year

    try:
        es_propietario, nombre = _es_propietario_anio(cntrcod, anio_actual)
        detalle = listar_deudas_detalle(cntrcod)
    except Exception as exc:  # pragma: no cover
        print(f"[deuda] comprobar_deuda error: {exc!r}")
        return {
            "cntrcod": cntrcod,
            "nombre": None,
            "estado_busta_card": EstadoBustaCard.ERROR,
            "tiene_deuda": True,
            "deuda_total": 0.0,
            "mensaje": "Error de conexion al validar deuda. Intente nuevamente.",
            "anio": anio_actual,
        }

    deuda_total = round(sum(d["saldo_pendiente"] for d in detalle), 2)

    if not es_propietario:
        return {
            "cntrcod": cntrcod,
            "nombre": nombre,
            "estado_busta_card": EstadoBustaCard.NO_PROPIETARIO,
            "tiene_deuda": True,
            "deuda_total": deuda_total,
            "mensaje": (
                f"ATENCION: El contribuyente no registra propiedades a su "
                f"nombre en el año {anio_actual}."
            ),
            "anio": anio_actual,
        }

    if deuda_total > 0:
        return {
            "cntrcod": cntrcod,
            "nombre": nombre,
            "estado_busta_card": EstadoBustaCard.TIENE_DEUDA,
            "tiene_deuda": True,
            "deuda_total": deuda_total,
            "mensaje": (
                "ATENCION: El contribuyente presenta deuda pendiente. "
                "Emision denegada hasta cancelarla."
            ),
            "anio": anio_actual,
        }

    return {
        "cntrcod": cntrcod,
        "nombre": nombre,
        "estado_busta_card": EstadoBustaCard.AL_DIA,
        "tiene_deuda": False,
        "deuda_total": 0.0,
        "mensaje": "El contribuyente no registra deudas. Procede la emision de BustaCard.",
        "anio": anio_actual,
    }
