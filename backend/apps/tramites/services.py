"""
Consultas contra `tramites_db` (dbControl) para exponer al ciudadano
los expedientes que ha presentado en SIAP.

El codigo de documento DOC00030 identifica a los expedientes.
"""
from __future__ import annotations

import datetime
import os
import re
import uuid
from typing import Any

from django.conf import settings
from django.db import connections

from apps.externos_tramites.models import (
    Documentos,
    DocumentosExternos,
    Ingresos,
    IngresosExternos,
    Oficinas,
    Propietarios,
    Proveidos,
    Solicitudes,
    SolicitudesExternas,
)


# DOC00030 sigue siendo el codigo del documento "Expediente" en `Documentos`,
# se usa solo para listar los expedientes ya existentes del contribuyente
# (tabla `Ingresos`). Para registrar un tramite nuevo en `IngresosExternos`
# usamos el codigo del catalogo externo `DocumentosExternos`: DOC00847.
COD_DOC_EXPEDIENTE = "DOC00030"          # Documentos -> Ingresos
COD_DOC_EXTERNO_TRAMITE = "DOC00847"     # DocumentosExternos -> IngresosExternos
COD_OFI_DEFAULT = "OFI00046"             # Mesa de partes (oficina recibe / verifica)

# Si el ciudadano no esta registrado en la mesa de partes virtual no tendra
# id_usuaext ni id_aspnetusers, y eso luego rompe el SP de aprobacion. En
# ese caso bloqueamos la creacion de tramites y le mandamos a registrarse.
LINK_REGISTRO_MESA_PARTES = (
    "http://mesa-partes-virtual.munibustamante.gob.pe:9090/Account/Register"
)


def obtener_documento_expediente() -> dict[str, Any] | None:
    """
    Devuelve el documento que se muestra en el formulario de Nuevo Tramite.
    Lo sacamos de `DocumentosExternos` (DOC00847) porque ese es el codigo
    que efectivamente se inserta en `IngresosExternos.cod_docext`.
    """
    doc = (
        DocumentosExternos.objects.using("tramites_db")
        .filter(cod_docext=COD_DOC_EXTERNO_TRAMITE)
        .first()
    )
    if not doc:
        return None
    return {
        "cod_doc": doc.cod_docext,
        "nom_doc": (doc.nom_docext or "").strip(),
        "sig_doc": "",
    }


def listar_solicitudes_tupa() -> list[dict[str, Any]]:
    """
    Lista de solicitudes externas (catalogo `SolicitudesExternas`).
    Ordenado por nom_solext. Conserva la forma {cod_sol, nom_sol} para no
    romper el contrato con el frontend.
    """
    qs = (
        SolicitudesExternas.objects.using("tramites_db")
        .all()
        .order_by("nom_solext")
    )
    return [
        {
            "cod_sol": s.cod_solext,
            "nom_sol": (s.nom_solext or "").strip(),
            "cod_ofi": "",
            "pla_sol": None,
        }
        for s in qs
    ]


def listar_oficinas() -> list[dict[str, Any]]:
    """Lista de oficinas activas (dbControl.Oficinas)."""
    qs = (
        Oficinas.objects.using("tramites_db")
        .filter(ofi_est=True)
        .order_by("nom_ofi")
    )
    return [
        {
            "cod_ofi": o.cod_ofi,
            "nom_ofi": (o.nom_ofi or "").strip(),
            "sig_ofi": (o.sig_ofi or "").strip(),
        }
        for o in qs
    ]


def _resolver_nombres_oficinas(cod_ofis) -> dict[str, str]:
    """
    Devuelve `{cod_ofi: nom_ofi}` para los codigos pedidos.

    Una sola query batch contra dbControl.Oficinas. Los codigos que no
    existan no aparecen en el dict — el caller decide el fallback (lo
    normal es dejar el codigo crudo si no se resuelve).
    """
    codigos = {c.strip() for c in (cod_ofis or []) if c and str(c).strip()}
    if not codigos:
        return {}
    qs = (
        Oficinas.objects.using("tramites_db")
        .filter(cod_ofi__in=codigos)
        .values("cod_ofi", "nom_ofi")
    )
    return {
        (o["cod_ofi"] or "").strip(): (o["nom_ofi"] or "").strip()
        for o in qs
    }


def _nombre_oficina_o_codigo(cod_ofi: str, mapa: dict[str, str]) -> str:
    """Devuelve el nombre legible de la oficina, o el codigo crudo si no esta en el mapa."""
    cod = (cod_ofi or "").strip()
    if not cod:
        return ""
    return mapa.get(cod) or cod


def obtener_oficina_default() -> dict[str, Any] | None:
    """Oficina por defecto OFI00046 (mesa de partes)."""
    o = (
        Oficinas.objects.using("tramites_db")
        .filter(cod_ofi=COD_OFI_DEFAULT)
        .first()
    )
    if not o:
        return None
    return {
        "cod_ofi": o.cod_ofi,
        "nom_ofi": (o.nom_ofi or "").strip(),
        "sig_ofi": (o.sig_ofi or "").strip(),
    }


def cod_pros_de_dni(dni: str) -> list[str]:
    """
    Devuelve TODOS los cod_pro de Propietarios asociados a la misma persona
    (mismo MPV) que el DNI dado. Maneja dos tipos de duplicidad observada:

      a) Mismo DNI con N filas y distinto cod_pro (PRO0005526 / PRO0090528).
      b) Distintos identificadores en `dni_pro` (DNI vs pasaporte) pero
         comparten `id_usuaext` / `id_aspnetusers` (la misma cuenta MPV
         tiene dos Propietarios con DNI distinto).

    Algoritmo:
      1. Semilla: filas donde LTRIM(RTRIM(dni_pro)) = dni.
      2. Recolectamos id_usuaext y id_aspnetusers no vacios de la semilla.
      3. Buscamos todas las filas que comparten cualquiera de esos IDs MPV
         con la semilla, y las sumamos al conjunto de cod_pros.

    Usamos raw SQL para que el LTRIM/RTRIM se ejecute server-side y para
    bypassear el router read-only sin pelearnos con el ORM.
    """
    if not dni:
        return []
    dni = dni.strip()

    cod_pros: set[str] = set()
    id_usuaexts: set[int] = set()
    id_aspnets: set[str] = set()

    try:
        with connections["tramites_db"].cursor() as cursor:
            # 1) Semilla: filas con este DNI
            cursor.execute(
                "SELECT cod_pro, id_usuaext, id_aspnetusers "
                "FROM Propietarios WITH (NOLOCK) "
                "WHERE LTRIM(RTRIM(dni_pro)) = %s",
                [dni],
            )
            for cod_pro, id_usua, id_aspnet in cursor.fetchall():
                if cod_pro:
                    cod_pros.add(cod_pro.strip())
                if id_usua is not None:
                    id_usuaexts.add(int(id_usua))
                if id_aspnet and id_aspnet.strip():
                    id_aspnets.add(id_aspnet.strip())

            # 2) Filas que comparten id_usuaext con la semilla
            if id_usuaexts:
                placeholders = ",".join(["%s"] * len(id_usuaexts))
                cursor.execute(
                    f"SELECT cod_pro FROM Propietarios WITH (NOLOCK) "
                    f"WHERE id_usuaext IN ({placeholders})",
                    list(id_usuaexts),
                )
                for (cod_pro,) in cursor.fetchall():
                    if cod_pro:
                        cod_pros.add(cod_pro.strip())

            # 3) Filas que comparten id_aspnetusers con la semilla
            if id_aspnets:
                placeholders = ",".join(["%s"] * len(id_aspnets))
                cursor.execute(
                    f"SELECT cod_pro FROM Propietarios WITH (NOLOCK) "
                    f"WHERE LTRIM(RTRIM(id_aspnetusers)) IN ({placeholders})",
                    list(id_aspnets),
                )
                for (cod_pro,) in cursor.fetchall():
                    if cod_pro:
                        cod_pros.add(cod_pro.strip())
    except Exception as exc:  # pragma: no cover
        print(f"[tramites] cod_pros_de_dni({dni!r}) error: {exc!r}")
        return []

    resultado = sorted(cod_pros)
    print(
        f"[tramites] cod_pros_de_dni({dni!r}) -> {len(resultado)} match(es) | "
        f"id_usuaext={sorted(id_usuaexts)} id_aspnet={sorted(id_aspnets)} | "
        f"cod_pros={resultado}"
    )
    return resultado


def _estado_display(ing: Ingresos) -> tuple[str, str]:
    """
    Reglas de estado para un ingreso de SIAP:
      - est_eli = True  -> Archivado (eliminado / cerrado)
      - est_obs = True  -> Observado (mesa de partes pidio correccion)
      - cualquier otra cosa -> En tramite

    Antes interpretabamos `est_sol = False` como Resuelto, pero ese flag no
    significa eso en SIAP (todos los registros nuevos vienen con est_sol
    apagado y eso no quiere decir que el tramite haya terminado). El estado
    final en SIAP se ve como "EN TRAMITE / PENDIENTE" en el form de
    Tramite Documentario, asi que por defecto los marcamos como En tramite.
    """
    if ing.est_eli:
        return "ARCHIVADO", "Archivado"
    if ing.est_obs:
        return "OBSERVADO", "Observado"
    return "EN_TRAMITE", "En tramite"


def listar_expedientes_contribuyente(cod_pros: list[str] | str) -> list[dict[str, Any]]:
    """
    Devuelve los expedientes (cod_doc = DOC00030) del contribuyente, ordenados
    por fecha de ingreso descendente.

    Acepta un cod_pro suelto (string) o una lista de cod_pros. Un DNI suele
    tener varios cod_pro hermanos en Propietarios; consultamos por todos
    para no perder los expedientes que estan bajo cod_pros antiguos.
    """
    if isinstance(cod_pros, str):
        cod_pros = [cod_pros]
    cod_pros = [c.strip() for c in (cod_pros or []) if c and c.strip()]
    if not cod_pros:
        print("[tramites] listar_expedientes_contribuyente: lista de cod_pros vacia")
        return []

    ingresos = list(
        Ingresos.objects.using("tramites_db")
        .filter(cod_pro_id__in=cod_pros, cod_doc_id=COD_DOC_EXPEDIENTE)
        .select_related("cod_sol")
        .order_by("-fec_ing")
    )
    print(
        f"[tramites] listar: cod_pros={cod_pros} cod_doc={COD_DOC_EXPEDIENTE} "
        f"-> {len(ingresos)} expedientes"
    )

    if not ingresos:
        # Diagnostico: ¿cuantos hay sin filtrar por cod_doc?
        total = (
            Ingresos.objects.using("tramites_db")
            .filter(cod_pro_id__in=cod_pros)
            .count()
        )
        if total:
            docs_set = list(
                Ingresos.objects.using("tramites_db")
                .filter(cod_pro_id__in=cod_pros)
                .values_list("cod_doc_id", flat=True)
                .distinct()
            )
            print(
                f"[tramites] WARN: {total} ingresos para esos cod_pros pero "
                f"ninguno con cod_doc={COD_DOC_EXPEDIENTE}. "
                f"Docs encontrados: {docs_set}"
            )
        else:
            print(
                f"[tramites] WARN: 0 ingresos para cod_pros={cod_pros}. "
                "El query no engancha — revisar tipo/padding de la columna."
            )

    cod_ings = [i.cod_ing for i in ingresos]
    conteo_prov: dict[int, int] = {}
    ultimo_prov: dict[int, Proveidos] = {}
    if cod_ings:
        proveidos = (
            Proveidos.objects.using("tramites_db")
            .filter(cod_ing_id__in=cod_ings)
            .order_by("cod_ing_id", "-fec_prov")
        )
        for p in proveidos:
            conteo_prov[p.cod_ing_id] = conteo_prov.get(p.cod_ing_id, 0) + 1
            ultimo_prov.setdefault(p.cod_ing_id, p)

    # Recolectar todos los cod_ofi para una sola query a Oficinas
    cod_ofis: set[str] = set()
    for ing in ingresos:
        if ing.ofi_tra:
            cod_ofis.add(ing.ofi_tra.strip())
    for p in ultimo_prov.values():
        if p.ofi_tra:
            cod_ofis.add(p.ofi_tra.strip())
    nombres_ofi = _resolver_nombres_oficinas(cod_ofis)

    resultado: list[dict[str, Any]] = []
    for ing in ingresos:
        estado, estado_display = _estado_display(ing)
        sol: Solicitudes | None = ing.cod_sol if ing.cod_sol_id else None
        ultimo = ultimo_prov.get(ing.cod_ing)
        resultado.append({
            "id": ing.cod_ing,
            "numero": (ing.num_doc or "").strip(),
            "asunto": (ing.des_sol or "").strip(),
            "tipo_codigo": ing.cod_sol_id,
            "tipo_nombre": (sol.nom_sol.strip() if sol and sol.nom_sol else ""),
            "estado": estado,
            "estado_display": estado_display,
            "observacion": (ing.obs_req or "").strip() if ing.est_obs else "",
            "fecha_ingreso": ing.fec_ing.isoformat() if ing.fec_ing else None,
            "fecha_vencimiento": ing.fec_ven.isoformat() if ing.fec_ven else None,
            "oficina_actual": _nombre_oficina_o_codigo(ing.ofi_tra, nombres_ofi),
            "cantidad_proveidos": conteo_prov.get(ing.cod_ing, 0),
            "ultimo_proveido": (
                {
                    "fecha": ultimo.fec_prov.isoformat() if ultimo.fec_prov else None,
                    "numero": (ultimo.num_prov or "").strip(),
                    "accion": (ultimo.acc_tom or "").strip(),
                    "oficina": _nombre_oficina_o_codigo(ultimo.ofi_tra, nombres_ofi),
                }
                if ultimo
                else None
            ),
        })
    return resultado


def listar_ingresos_externos_pendientes(id_usuaext: int | None) -> list[dict[str, Any]]:
    """
    Tramites que el ciudadano envio por MPV / app y aun NO han pasado por
    el SP de aprobacion (cod_expext IS NULL). Una vez aprobados, el SP los
    copia a `Ingresos` y dejan de mostrarse aqui (los toma el listado
    principal `listar_expedientes_contribuyente`).
    """
    if not id_usuaext:
        return []

    qs = (
        IngresosExternos.objects.using("tramites_db")
        .filter(id_usuaext=id_usuaext, cod_expext__isnull=True)
        .order_by("-fec_ingext")
    )

    # Diccionario de codigos de solicitud -> nombre legible
    cod_sols = {(s.cod_solext or "").strip() for s in qs if s.cod_solext}
    nombres_sol: dict[str, str] = {}
    if cod_sols:
        sols = (
            SolicitudesExternas.objects.using("tramites_db")
            .filter(cod_solext__in=[c for c in cod_sols if c])
            .values("cod_solext", "nom_solext")
        )
        for s in sols:
            nombres_sol[s["cod_solext"]] = (s["nom_solext"] or "").strip()

    # Nombres de oficinas (cod_ofi -> nom_ofi) para mostrar legible en el app
    nombres_ofi = _resolver_nombres_oficinas({
        e.ofi_recext for e in qs if e.ofi_recext
    })

    resultado: list[dict[str, Any]] = []
    for e in qs:
        sol_cod = (e.cod_solext or "").strip()
        resultado.append({
            "id": e.cod_ingext,
            "numero": (e.num_docext or "").strip(),
            "asunto": (e.des_solext or "").strip(),
            "tipo_codigo": sol_cod,
            "tipo_nombre": nombres_sol.get(sol_cod, ""),
            "estado": "EN_TRAMITE",
            "estado_display": "Pendiente de aprobacion",
            "observacion": "",
            "fecha_ingreso": e.fec_ingext.isoformat() if e.fec_ingext else None,
            "fecha_vencimiento": e.fec_venext.isoformat() if e.fec_venext else None,
            "oficina_actual": _nombre_oficina_o_codigo(e.ofi_recext, nombres_ofi),
            "cantidad_proveidos": 0,
            "ultimo_proveido": None,
            "origen": "INGRESOS_EXTERNOS",  # marca para distinguir
        })
    return resultado


def listar_tramites_contribuyente(
    cod_pros: list[str] | str,
    id_usuaext: int | None = None,
) -> list[dict[str, Any]]:
    """
    Vista unificada para "Mis tramites":
      - Aprobados / con linea de vida -> desde Ingresos por cod_pros
      - Pendientes de aprobacion (recien creados por app/MPV) -> desde
        IngresosExternos por id_usuaext, filtrando solo cod_expext IS NULL

    El front no diferencia mucho, pero internamente cada item lleva un
    campo `origen` para saber de cual tabla viene.
    """
    aprobados = listar_expedientes_contribuyente(cod_pros)
    for item in aprobados:
        item.setdefault("origen", "INGRESOS")

    pendientes = listar_ingresos_externos_pendientes(id_usuaext)

    combinado = pendientes + aprobados
    # Orden global por fecha desc
    combinado.sort(
        key=lambda x: x.get("fecha_ingreso") or "",
        reverse=True,
    )
    return combinado


def detalle_expediente_siap(
    cod_pros: list[str] | str, cod_ing: int
) -> dict[str, Any] | None:
    """
    Devuelve la cabecera del ingreso + la linea de vida (Proveidos) del
    expediente. Acepta una lista de cod_pros (todos los del DNI del usuario)
    para que aunque el expediente este registrado bajo un cod_pro hermano
    del que tenemos guardado en Ciudadano, igual lo encontremos. Si el
    cod_ing no pertenece a ningun cod_pro de la lista, retorna None.
    """
    if isinstance(cod_pros, str):
        cod_pros = [cod_pros]
    cod_pros = [c for c in (cod_pros or []) if c]
    if not cod_pros:
        return None

    ing = (
        Ingresos.objects.using("tramites_db")
        .select_related("cod_sol")
        .filter(cod_ing=cod_ing, cod_pro_id__in=cod_pros)
        .first()
    )
    if not ing:
        return None

    proveidos = (
        Proveidos.objects.using("tramites_db")
        .filter(cod_ing_id=cod_ing)
        .order_by("fec_prov", "cod_prov")
    )

    estado, estado_display = _estado_display(ing)
    sol: Solicitudes | None = ing.cod_sol if ing.cod_sol_id else None

    # Recolectar todos los cod_ofi de la cabecera + linea de vida y resolverlos
    # de una sola vez (1 query).
    cod_ofis: set[str] = set()
    if ing.ofi_tra:
        cod_ofis.add(ing.ofi_tra.strip())
    for p in proveidos:
        if p.cod_ofi:
            cod_ofis.add(p.cod_ofi.strip())
        if p.ofi_tra:
            cod_ofis.add(p.ofi_tra.strip())
    nombres_ofi = _resolver_nombres_oficinas(cod_ofis)

    linea_vida = []
    for p in proveidos:
        linea_vida.append({
            "id": p.cod_prov,
            "fecha": p.fec_prov.isoformat() if p.fec_prov else None,
            "numero": (p.num_prov or "").strip(),
            "tipo_documento": (p.cod_doc or "").strip(),
            "accion": (p.acc_tom or "").strip(),
            "oficina_origen": _nombre_oficina_o_codigo(p.cod_ofi, nombres_ofi),
            "oficina_destino": _nombre_oficina_o_codigo(p.ofi_tra, nombres_ofi),
            "fecha_recepcion": p.fec_rec.isoformat() if p.fec_rec else None,
            "recibido": bool(p.est_rec),
        })

    return {
        "id": ing.cod_ing,
        "numero": (ing.num_doc or "").strip(),
        "asunto": (ing.des_sol or "").strip(),
        "tipo_codigo": ing.cod_sol_id,
        "tipo_nombre": (sol.nom_sol.strip() if sol and sol.nom_sol else ""),
        "estado": estado,
        "estado_display": estado_display,
        "observacion": (ing.obs_req or "").strip() if ing.est_obs else "",
        "fecha_ingreso": ing.fec_ing.isoformat() if ing.fec_ing else None,
        "fecha_vencimiento": ing.fec_ven.isoformat() if ing.fec_ven else None,
        "oficina_actual": _nombre_oficina_o_codigo(ing.ofi_tra, nombres_ofi),
        "linea_vida": linea_vida,
    }


# =====================================================================
# REGISTRO DE NUEVO TRAMITE EN IngresosExternos
# =====================================================================

PLAZO_DEFAULT_DIAS = 30
DIR_ADJUNTOS = "tramites_externos"


class TramiteExternoError(Exception):
    """Cualquier fallo controlado durante el insert de IngresosExternos."""


def _ids_aspnet_para_user(user) -> tuple[int | None, str | None]:
    """
    Recupera (id_usuaext, id_aspnetusers) desde Propietarios usando
    user.cod_pro. Si no hay match -> (None, None).
    """
    cod_pro = getattr(user, "cod_pro", None)
    if not cod_pro:
        return (None, None)
    try:
        prop = (
            Propietarios.objects.using("tramites_db")
            .filter(cod_pro=cod_pro)
            .values("id_usuaext", "id_aspnetusers")
            .first()
        )
    except Exception as exc:  # pragma: no cover
        print(f"[tramite-externo] error leyendo Propietarios {cod_pro}: {exc!r}")
        return (None, None)
    if not prop:
        return (None, None)
    return (prop.get("id_usuaext"), prop.get("id_aspnetusers"))


def verificar_registro_mesa_partes(user) -> dict[str, Any]:
    """
    Indica si el ciudadano esta registrado en la mesa de partes virtual
    (tiene tanto id_usuaext como id_aspnetusers en Propietarios). Si falta
    cualquiera de los dos, devuelve `registrado=False` mas el link al
    portal externo para que se registre.
    """
    id_usua, id_aspnet = _ids_aspnet_para_user(user)
    registrado = bool(id_usua) and bool(id_aspnet and str(id_aspnet).strip())
    return {
        "registrado": registrado,
        "id_usuaext": id_usua,
        "id_aspnetusers": id_aspnet,
        "link_registro": LINK_REGISTRO_MESA_PARTES,
        "mensaje": (
            "Para iniciar tramites debes registrarte primero en la Mesa de "
            "Partes Virtual de la Municipalidad. Una vez registrado podras "
            "regresar al app y continuar."
        )
        if not registrado
        else "",
    }


def _sanear_nombre_archivo(nombre: str) -> str:
    base = os.path.basename(nombre or "").strip() or "documento.pdf"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", base)[:120]


def _guardar_archivo_local(cod_ingext: int, nombre: str, raw: bytes) -> str:
    """Guarda el PDF en MEDIA_ROOT/tramites_externos. Devuelve la ruta relativa."""
    if not raw:
        return ""
    safe = _sanear_nombre_archivo(nombre)
    target_dir = os.path.join(settings.MEDIA_ROOT, DIR_ADJUNTOS)
    os.makedirs(target_dir, exist_ok=True)
    final_name = f"{cod_ingext}_{safe}"
    final_path = os.path.join(target_dir, final_name)
    with open(final_path, "wb") as fh:
        fh.write(raw)
    return os.path.join(DIR_ADJUNTOS, final_name).replace("\\", "/")


# IngresosExternos tiene triggers AFTER INSERT (uno de ellos rellena
# num_docext = '{cod_ingext}-{year}'). Por eso:
#   - OUTPUT INSERTED.cod_ingext sin INTO revienta (error 334).
#   - SCOPE_IDENTITY() en una segunda llamada cursor.execute devuelve NULL
#     porque pyodbc / el trigger pierden el contexto.
# Solucion: batch unico con SET NOCOUNT ON + OUTPUT INSERTED.cod_ingext INTO
# una table variable, y al final un SELECT que devuelve la fila al cliente.
_SQL_INSERT_INGRESOEXT = """
SET NOCOUNT ON;
DECLARE @InsertedIds TABLE (cod_ingext INT);
INSERT INTO IngresosExternos (
    fec_ingext, cod_docext, num_docext, cod_solext, des_solext,
    ofi_traext, ofi_recext, fec_venext, doc_adjext,
    id_usuaext, id_aspnetusers, cod_expext, num_expext,
    nom_adjext, est_actext, obs_actext, fec_actext
)
OUTPUT INSERTED.cod_ingext INTO @InsertedIds
VALUES (%s, %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, NULL, NULL,
        %s, %s, %s, %s);
SELECT cod_ingext FROM @InsertedIds;
"""

_SQL_READ_NUMDOC = """
SELECT num_docext FROM IngresosExternos WITH (NOLOCK)
WHERE cod_ingext = %s;
"""

# Helper opcional: ultimo correlativo en num_docext para un year dado.
# Hoy no se usa (cod_ingext IDENTITY ya nos da el correlativo global), pero
# sirve si alguna vez hay que recomputar manualmente sin confiar en IDENTITY.
_SQL_MAX_NUM_DOCEXT_YEAR = """
SELECT MAX(CAST(LEFT(num_docext, CHARINDEX('-', num_docext) - 1) AS INT))
FROM IngresosExternos WITH (NOLOCK)
WHERE num_docext LIKE %s
  AND CHARINDEX('-', num_docext) > 0
  AND ISNUMERIC(LEFT(num_docext, CHARINDEX('-', num_docext) - 1)) = 1;
"""


def siguiente_correlativo_year(year: int) -> int:
    """
    Lee el max prefijo numerico de num_docext del year y devuelve max+1.
    Si no hay filas para ese year, devuelve 1.
    """
    try:
        with connections["tramites_db"].cursor() as cursor:
            cursor.execute(_SQL_MAX_NUM_DOCEXT_YEAR, [f"%-{year}"])
            row = cursor.fetchone()
    except Exception as exc:  # pragma: no cover
        print(f"[tramite-externo] error calculando correlativo {year}: {exc!r}")
        return 1
    if not row or row[0] is None:
        return 1
    return int(row[0]) + 1


def crear_ingreso_externo(
    *,
    user,
    cod_solext: str,
    des_solext: str,
    ofi_recext: str,
    ofi_traext: str,
    fec_solicitud: datetime.date | None = None,
    archivo_nombre: str | None = None,
    archivo_bytes: bytes | None = None,
    plazo_dias: int = PLAZO_DEFAULT_DIAS,
) -> dict[str, Any]:
    """
    Inserta una fila en `dbControl.IngresosExternos` para registrar un tramite
    iniciado desde el app movil.

    Columnas que llenamos: fec_ingext, cod_docext, num_docext (placeholder),
    cod_solext, des_solext, ofi_traext, ofi_recext, fec_venext, doc_adjext,
    id_usuaext, id_aspnetusers, nom_adjext.

    Columnas que dejamos en NULL (las llena el SP de aprobacion de SIAP):
      cod_expext, num_expext, est_actext, obs_actext, fec_actext.
    Si las llenamos al INSERT, un trigger AFTER INSERT copia la fila a la
    tabla `Ingresos` y eso es responsabilidad del proceso de aprobacion,
    no del registro inicial.
    """
    if not cod_solext:
        raise TramiteExternoError("cod_solext requerido.")
    if not des_solext or len(des_solext.strip()) < 5:
        raise TramiteExternoError("des_solext muy corto (>= 5 chars).")

    ahora = datetime.datetime.now()
    base_fecha = (
        datetime.datetime.combine(fec_solicitud, datetime.time.min)
        if isinstance(fec_solicitud, datetime.date)
        else ahora
    )
    fec_ven = base_fecha + datetime.timedelta(days=int(plazo_dias))

    id_usua, id_aspnet = _ids_aspnet_para_user(user)
    if not id_usua or not (id_aspnet and str(id_aspnet).strip()):
        raise TramiteExternoError(
            "El ciudadano no esta registrado en la Mesa de Partes Virtual. "
            f"Debe registrarse en {LINK_REGISTRO_MESA_PARTES} antes de "
            "iniciar un tramite."
        )

    nom_adj = _sanear_nombre_archivo(archivo_nombre) if archivo_nombre else None
    doc_blob = archivo_bytes if archivo_bytes else None

    # num_docext es NOT NULL: metemos un placeholder unico para el INSERT
    # (varchar 20). Luego del SCOPE_IDENTITY actualizamos al valor real
    # '{cod_ingext}-{year}' para que el correlativo coincida con el ID
    # autogenerado por IDENTITY.
    placeholder_numdoc = f"P{uuid.uuid4().hex[:10]}"  # 11 chars

    params = [
        base_fecha,
        COD_DOC_EXTERNO_TRAMITE,
        placeholder_numdoc,                # num_docext temporal
        cod_solext,
        des_solext.strip().upper(),
        (ofi_traext or COD_OFI_DEFAULT).strip(),
        (ofi_recext or COD_OFI_DEFAULT).strip(),
        fec_ven,
        doc_blob,
        id_usua,
        id_aspnet,
        nom_adj,
        None,                              # est_actext: lo setea el SP
        None,                              # obs_actext: lo setea el SP
        None,                              # fec_actext: lo setea el SP
    ]

    print(
        "[tramite-externo] INSERT params: "
        f"cod_solext={cod_solext!r} ofi_rec={params[6]!r} ofi_tra={params[5]!r} "
        f"fec_ingext={params[0]!r} fec_ven={params[7]!r} "
        f"id_usua={id_usua!r} id_aspnet={id_aspnet!r} "
        f"nom_adj={nom_adj!r} doc_size={len(doc_blob) if doc_blob else 0}"
    )

    cod_ingext: int | None = None
    num_docext: str | None = None
    try:
        with connections["tramites_db"].cursor() as cursor:
            cursor.execute(_SQL_INSERT_INGRESOEXT, params)
            row = cursor.fetchone()
            if row and row[0] is not None:
                cod_ingext = int(row[0])

            # Fallback: si los triggers se comieron el SELECT de @InsertedIds,
            # buscamos la fila por el placeholder unico que metimos.
            if cod_ingext is None:
                print(
                    "[tramite-externo] OUTPUT vacio, buscando por placeholder "
                    f"{placeholder_numdoc!r}"
                )
                cursor.execute(
                    "SELECT TOP 1 cod_ingext FROM IngresosExternos "
                    "WHERE num_docext = %s ORDER BY cod_ingext DESC",
                    [placeholder_numdoc],
                )
                row = cursor.fetchone()
                if row and row[0] is not None:
                    cod_ingext = int(row[0])

            if cod_ingext is None:
                raise TramiteExternoError(
                    "INSERT corrio pero no pudimos recuperar cod_ingext."
                )

            # NO hacemos UPDATE de num_docext: SIAP tiene un trigger AFTER
            # INSERT que ya lo rellena ('{cod_ingext}-{year}'). Si hicieramos
            # UPDATE, otro trigger AFTER UPDATE replicaria la fila a Ingresos
            # y eso es responsabilidad del proceso de aprobacion de SIAP, no
            # del registro inicial. Solo leemos lo que el trigger dejo.
            cursor.execute(_SQL_READ_NUMDOC, [cod_ingext])
            row = cursor.fetchone()
            num_docext = (row[0] or "").strip() if row else None

            # Si el trigger no llego a setear num_docext (raro), construimos
            # el valor por defecto '{cod_ingext}-{year}' solo para devolverlo
            # al cliente. NO lo escribimos en la BD.
            if not num_docext or num_docext == placeholder_numdoc:
                print(
                    f"[tramite-externo] WARNING: trigger no seteo num_docext "
                    f"para cod_ingext={cod_ingext}, sigue como "
                    f"{num_docext!r}. La fila queda con el placeholder."
                )
                num_docext = f"{cod_ingext}-{ahora.year}"
    except TramiteExternoError:
        raise
    except Exception as exc:  # pragma: no cover
        print(f"[tramite-externo] error insertando IngresosExternos: {exc!r}")
        raise TramiteExternoError(
            f"No se pudo registrar el tramite en SIAP: {exc}"
        ) from exc

    ruta_local = _guardar_archivo_local(cod_ingext, nom_adj or "", archivo_bytes or b"")

    return {
        "cod_ingext": cod_ingext,
        "num_docext": num_docext,
        "cod_docext": COD_DOC_EXTERNO_TRAMITE,
        "cod_solext": cod_solext,
        "fec_ingext": base_fecha.isoformat(),
        "fec_venext": fec_ven.isoformat(),
        "id_usuaext": id_usua,
        "id_aspnetusers": id_aspnet,
        "nom_adjext": nom_adj,
        "doc_adjext_guardado": doc_blob is not None,
        "doc_adjext_size": len(doc_blob) if doc_blob else 0,
        "archivo_local": ruta_local or None,
    }
