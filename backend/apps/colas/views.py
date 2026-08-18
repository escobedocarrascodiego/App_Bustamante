"""
Vistas del gestor de turnos.

Pantallas (HTML):
  GET /colas/                 -> hub con los 3 enlaces
  GET /colas/kiosko/          -> sacar turno (publico, autoservicio)
  GET /colas/tv/              -> pantalla LED de turnos (publico)
  GET /colas/ventanilla/      -> modulo del ventanillero (staff)

Endpoints (JSON):
  POST /colas/api/emitir/        -> emite turno (publico, kiosko)
  GET  /colas/api/tv-estado/     -> estado para la TV (publico)
  GET  /colas/api/mi-ventanilla/ -> estado de la ventanilla del operador (staff)
  POST /colas/api/abrir/         -> abrir una ventanilla (staff)
  POST /colas/api/accion/        -> llamar/iniciar/finalizar/... (staff)
"""
from __future__ import annotations

import json

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from . import services
from .models import Servicio, Turno, Ventanilla


# ---------------------------------------------------------------------------
# Helpers de serializacion
# ---------------------------------------------------------------------------


def _turno_dict(t: Turno | None) -> dict | None:
    if not t:
        return None
    return {
        "codigo": t.codigo,
        "servicio": t.servicio.nombre,
        "prioritario": t.prioritario,
        "dni": t.dni,
        "nombre": t.nombre,
        "estado": t.estado,
    }


def _body(request) -> dict:
    if request.content_type and "application/json" in request.content_type:
        try:
            return json.loads(request.body or b"{}")
        except (ValueError, TypeError):
            return {}
    return request.POST.dict()


# ---------------------------------------------------------------------------
# Pantallas (HTML)
# ---------------------------------------------------------------------------


def index_view(request):
    return render(request, "colas/index.html", {})


def kiosko_view(request):
    servicios = Servicio.objects.filter(activo=True).order_by("orden", "nombre")
    return render(request, "colas/kiosko.html", {"servicios": servicios})


def tv_view(request):
    return render(request, "colas/tv.html", {})


@staff_member_required
@ensure_csrf_cookie
def ventanilla_view(request):
    ventanillas = Ventanilla.objects.filter(activa=True).order_by("numero")
    servicios = Servicio.objects.filter(activo=True).order_by("orden", "nombre")
    return render(
        request,
        "colas/ventanilla.html",
        {"ventanillas": ventanillas, "servicios": servicios},
    )


# ---------------------------------------------------------------------------
# Endpoints JSON
# ---------------------------------------------------------------------------


@csrf_exempt
@require_POST
def emitir_endpoint(request):
    """Emite un turno desde el kiosko. DNI y preferente son opcionales."""
    data = _body(request)
    try:
        servicio_id = int(data.get("servicio_id"))
    except (TypeError, ValueError):
        return JsonResponse({"detail": "servicio_id invalido."}, status=400)

    servicio = Servicio.objects.filter(id=servicio_id, activo=True).first()
    if not servicio:
        return JsonResponse({"detail": "Servicio no encontrado."}, status=404)

    dni = (str(data.get("dni") or "")).strip()
    nombre = (str(data.get("nombre") or "")).strip()
    prioritario = bool(data.get("prioritario"))

    turno = services.emitir_turno(
        servicio,
        prioritario=prioritario,
        dni=dni,
        nombre=nombre,
        canal=Turno.Canal.KIOSKO,
    )

    # Datos completos para imprimir el ticket 80mm en el kiosko. La hora la
    # pone el SERVIDOR (creado_en), no el reloj del kiosko, para consistencia.
    from django.utils import timezone

    creado = timezone.localtime(turno.creado_en)
    barcode_valor = turno.dni or turno.codigo
    barcode_svg = ""
    barcode_texto = ""
    try:
        from apps.tarjetas import barcode128

        barcode_svg = barcode128.svg(barcode_valor, height=48)
        barcode_texto = barcode128.texto_humano(barcode_valor)
    except Exception as exc:  # pragma: no cover
        print(f"[colas] barcode ticket {barcode_valor!r} fallo: {exc!r}")

    return JsonResponse(
        {
            "codigo": turno.codigo,
            "numero": turno.numero,
            "servicio": servicio.nombre,
            "prioritario": turno.prioritario,
            "personas_adelante": services.personas_adelante(turno),
            "nombre": turno.nombre,
            "fecha": creado.strftime("%d/%m/%Y"),
            "hora": creado.strftime("%H:%M"),
            "barcode_svg": barcode_svg,
            "barcode_texto": barcode_texto,
        },
        status=201,
    )


@require_GET
def buscar_dni_endpoint(request):
    """Busca un DNI en CONTRIBUYENTES para autocompletar el nombre en el kiosko."""
    dni = (request.GET.get("dni") or "").strip()
    if not dni:
        return JsonResponse({"encontrado": False, "nombre": ""})
    try:
        from apps.deudas.services import buscar_contribuyentes

        for c in buscar_contribuyentes(dni, limite=5):
            if c.get("dni") == dni:
                return JsonResponse({"encontrado": True, "nombre": c.get("nombre", "")})
    except Exception as exc:  # pragma: no cover
        print(f"[colas] buscar-dni {dni!r} fallo: {exc!r}")
    return JsonResponse({"encontrado": False, "nombre": ""})


@require_GET
def tv_estado_endpoint(request):
    """Estado para la TV: ventanillas + llamados activos + siguientes en espera."""
    from django.db.models.functions import Coalesce
    from django.utils import timezone

    hoy = timezone.localdate()
    ventanillas = (
        Ventanilla.objects.filter(activa=True)
        .select_related("turno_actual")
        .order_by("numero")
    )
    data_v = []
    llamando = []
    for v in ventanillas:
        turno = v.turno_actual
        data_v.append({
            "numero": v.numero,
            "nombre": v.nombre or f"Ventanilla {v.numero}",
            "estado": v.estado,
            "estado_label": v.get_estado_display(),
            "turno": turno.codigo if turno else None,
        })
        if v.estado == Ventanilla.Estado.LLAMANDO and turno:
            llamando.append({
                "codigo": turno.codigo,
                "nombre": turno.nombre or "—",
                "ventanilla": v.numero,
                "prioritario": turno.prioritario,
                "actualizado": v.actualizado_en.timestamp(),
            })
    # Mas reciente primero
    llamando.sort(key=lambda x: x["actualizado"], reverse=True)

    # Siguientes (en espera), preferentes primero y luego por orden de llegada.
    en_espera = [
        {
            "codigo": t.codigo,
            "nombre": t.nombre or "—",
            "servicio": t.servicio.nombre,
            "prioritario": t.prioritario,
        }
        for t in (
            Turno.objects.filter(fecha=hoy, estado=Turno.Estado.EN_ESPERA)
            .select_related("servicio")
            .annotate(orden=Coalesce("en_cola_desde", "creado_en"))
            .order_by("-prioritario", "orden")[:12]
        )
    ]

    return JsonResponse(
        {"ventanillas": data_v, "llamando": llamando, "en_espera": en_espera}
    )


@staff_member_required
@require_GET
def mi_ventanilla_endpoint(request):
    """Estado de la ventanilla del operador logueado + su cola."""
    ventanilla = services.ventanilla_de(request.user)
    if not ventanilla:
        # Lista de ventanillas disponibles para abrir
        libres = list(
            Ventanilla.objects.filter(activa=True)
            .order_by("numero")
            .values("numero", "estado")
        )
        return JsonResponse({"tiene_ventanilla": False, "ventanillas": libres})

    servicios_ids = list(ventanilla.servicios.values_list("id", flat=True))
    from django.utils import timezone

    en_espera_qs = Turno.objects.filter(
        fecha=timezone.localdate(),
        estado=Turno.Estado.EN_ESPERA,
        servicio_id__in=servicios_ids,
    ).order_by("-prioritario", "creado_en")

    proximos = [
        {"codigo": t.codigo, "prioritario": t.prioritario}
        for t in en_espera_qs[:5]
    ]

    return JsonResponse({
        "tiene_ventanilla": True,
        "numero": ventanilla.numero,
        "estado": ventanilla.estado,
        "estado_label": ventanilla.get_estado_display(),
        "turno_actual": _turno_dict(ventanilla.turno_actual),
        "en_espera": en_espera_qs.count(),
        "proximos": proximos,
    })


@staff_member_required
@require_POST
def abrir_endpoint(request):
    data = _body(request)
    try:
        numero = int(data.get("numero"))
    except (TypeError, ValueError):
        return JsonResponse({"detail": "numero invalido."}, status=400)
    try:
        services.abrir_ventanilla(request.user, numero)
    except Ventanilla.DoesNotExist:
        return JsonResponse({"detail": "Ventanilla no existe."}, status=404)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=409)
    return JsonResponse({"ok": True})


@staff_member_required
@require_POST
def accion_endpoint(request):
    """Acciones del ventanillero sobre SU ventanilla."""
    data = _body(request)
    accion = (data.get("accion") or "").strip()
    ventanilla = services.ventanilla_de(request.user)
    if not ventanilla:
        return JsonResponse({"detail": "No tienes una ventanilla abierta."}, status=409)

    resultado = {}
    if accion == "llamar":
        t = services.llamar_siguiente(ventanilla)
        if not t:
            return JsonResponse({"detail": "No hay turnos en espera."}, status=200)
        resultado = {"turno": t.codigo}
    elif accion == "rellamar":
        services.rellamar(ventanilla)
    elif accion == "iniciar":
        services.iniciar_atencion(ventanilla)
    elif accion == "finalizar":
        services.finalizar(ventanilla)
    elif accion == "ausente":
        services.marcar_ausente(ventanilla)
    elif accion == "pausar":
        services.pausar_ventanilla(ventanilla)
    elif accion == "reanudar":
        services.reanudar_ventanilla(ventanilla)
    elif accion == "cerrar":
        services.cerrar_ventanilla(ventanilla)
    elif accion == "derivar":
        try:
            destino_id = int(data.get("servicio_destino_id"))
        except (TypeError, ValueError):
            return JsonResponse({"detail": "servicio_destino_id invalido."}, status=400)
        destino = Servicio.objects.filter(id=destino_id, activo=True).first()
        if not destino:
            return JsonResponse({"detail": "Servicio destino no existe."}, status=404)
        nuevo = services.derivar(ventanilla, destino)
        resultado = {"nuevo_turno": nuevo.codigo if nuevo else None}
    else:
        return JsonResponse({"detail": f"Accion desconocida: {accion}"}, status=400)

    return JsonResponse({"ok": True, **resultado})
