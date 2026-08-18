"""
Modulo de VENTANILLA (uso interno de la municipalidad).

Permite a un administrador, desde una PC de la municipalidad, buscar a un
contribuyente (por DNI, nombre o codigo) y generar/imprimir su BustaCard
cuando NO tiene deuda. Pensado para vecinos que no usan el app movil.

Rutas (todas requieren sesion de staff — reusa el login del admin de Django):
  GET /genera_bustacard/                 -> buscador
  GET /genera_bustacard/<cntrcod>/       -> verifica deuda y genera la card
"""
from __future__ import annotations

import base64
import datetime
import hashlib
from functools import lru_cache
from pathlib import Path

from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.safestring import mark_safe

from apps.deudas.services import (
    EstadoBustaCard,
    buscar_contribuyentes,
    comprobar_deuda,
    listar_deudas_detalle,
    obtener_contribuyente,
)
from apps.tarjetas import barcode128
from apps.tarjetas.models import BustaCardVentanilla, TarjetaCiudadana

try:
    from apps.ciudadanos.models import Ciudadano
except Exception:  # pragma: no cover
    Ciudadano = None  # type: ignore


_LOGO_PATH = Path(__file__).resolve().parent / "static" / "ventanilla" / "logo.png"


@lru_cache(maxsize=1)
def _logo_data_uri() -> str:
    """Logo municipal como data URI (base64) para que la impresion no dependa
    del servidor de estaticos / funcione offline."""
    try:
        data = _LOGO_PATH.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception:  # pragma: no cover
        return ""


def _codigo_y_vencimiento(dni: str, cntrcod: int) -> tuple[str, datetime.date]:
    """
    Devuelve (codigo, fecha_vencimiento) para la card.

    La BustaCard SIEMPRE vence el 31 de diciembre del año en curso (certifica
    estar al dia en el ejercicio). Si el contribuyente ya tiene un Ciudadano
    con TarjetaCiudadana, reusa su codigo (consistencia con el app), pero el
    vencimiento se recalcula al año actual.
    """
    fin_anio = datetime.date(timezone.localdate().year, 12, 31)

    if Ciudadano is not None and dni:
        tarjeta = (
            TarjetaCiudadana.objects.filter(ciudadano__dni=dni)
            .order_by("-fecha_emision")
            .first()
        )
        if tarjeta:
            return tarjeta.codigo, fin_anio

    semilla = f"{dni}-{cntrcod}".encode("utf-8")
    codigo = "JLBR-" + hashlib.sha1(semilla).hexdigest()[:8].upper()
    return codigo, fin_anio


@staff_member_required
def buscar_view(request):
    """Buscador de contribuyentes."""
    term = (request.GET.get("q") or "").strip()
    resultados = buscar_contribuyentes(term) if term else []
    return render(
        request,
        "ventanilla/buscar.html",
        {
            "term": term,
            "resultados": resultados,
            "busco": bool(term),
            "logo": _logo_data_uri(),
        },
    )


@staff_member_required
def bustacard_view(request, cntrcod: int):
    """Verifica deuda y genera la BustaCard (o muestra la deuda pendiente)."""
    contribuyente = obtener_contribuyente(cntrcod)
    if not contribuyente:
        return render(
            request,
            "ventanilla/bustacard.html",
            {"no_encontrado": True, "cntrcod": cntrcod},
        )

    verificacion = comprobar_deuda(cntrcod)
    estado = verificacion["estado_busta_card"]
    al_dia = estado == EstadoBustaCard.AL_DIA

    contexto = {
        "contribuyente": contribuyente,
        "verificacion": verificacion,
        "al_dia": al_dia,
        "estado": estado,
        "hoy": timezone.localdate(),
        "logo": _logo_data_uri(),
    }

    if al_dia:
        codigo, fvenc = _codigo_y_vencimiento(
            contribuyente["dni"], contribuyente["cntrcod"]
        )
        dni = contribuyente["dni"]
        _registrar_emision(request, contribuyente, codigo, fvenc)
        contexto.update({
            "codigo": codigo,
            "fecha_vencimiento": fvenc,
            "anio": timezone.localdate().year,
            "barcode_svg": mark_safe(barcode128.svg(dni, height=64)),
            "barcode_texto": barcode128.texto_humano(dni),
        })
    else:
        # Con deuda: mostramos el detalle para informar al vecino.
        items = listar_deudas_detalle(cntrcod)
        items = [i for i in items if float(i.get("saldo_pendiente") or 0) > 0.009]
        items.sort(key=lambda i: (i.get("origen") or "", i.get("anio") or 0))
        contexto["items"] = items
        contexto["deuda_total"] = verificacion.get("deuda_total", 0.0)

    return render(request, "ventanilla/bustacard.html", contexto)


@staff_member_required
def bustacard_pdf_view(request, cntrcod: int):
    """Descarga la BustaCard en PDF (solo si el contribuyente esta al dia)."""
    from apps.tarjetas import pdf as pdf_mod

    contribuyente = obtener_contribuyente(cntrcod)
    if not contribuyente:
        raise Http404("Contribuyente no encontrado.")

    verificacion = comprobar_deuda(cntrcod)
    if verificacion["estado_busta_card"] != EstadoBustaCard.AL_DIA:
        # No procede el PDF si tiene deuda: lo mandamos de vuelta a la pagina.
        raise Http404("El contribuyente no esta al dia; no procede la BustaCard.")

    codigo, fvenc = _codigo_y_vencimiento(
        contribuyente["dni"], contribuyente["cntrcod"]
    )
    _registrar_emision(request, contribuyente, codigo, fvenc)
    contenido = pdf_mod.generar_bustacard_pdf(
        nombre=contribuyente["nombre"],
        dni=contribuyente["dni"],
        direccion=contribuyente["direccion"],
        codigo=codigo,
        anio=timezone.localdate().year,
        fecha_vencimiento=fvenc,
    )

    dni = contribuyente["dni"] or str(cntrcod)
    resp = HttpResponse(contenido, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="BustaCard_{dni}.pdf"'
    return resp


def _registrar_emision(request, contribuyente: dict, codigo: str, fvenc) -> None:
    """
    Registra (o actualiza) la emision de la BustaCard en el historial.
    get_or_create por (cntrcod, año): re-imprimir el mismo año no duplica.
    """
    try:
        BustaCardVentanilla.objects.get_or_create(
            cntrcod=contribuyente["cntrcod"],
            anio=timezone.localdate().year,
            defaults={
                "dni": contribuyente["dni"],
                "nombre": contribuyente["nombre"],
                "codigo": codigo,
                "fecha_vencimiento": fvenc,
                "emitido_por": getattr(request.user, "username", "") or "",
            },
        )
    except Exception as exc:  # pragma: no cover
        print(f"[ventanilla] no se pudo registrar emision: {exc!r}")


@staff_member_required
def historial_view(request):
    """
    Historial unificado de BustaCards emitidas:
      - Ventanilla (modelo BustaCardVentanilla)
      - App movil (TarjetaCiudadana)
    Muestra vigencia, titular, codigo, fechas y origen. Con busqueda y paginado.
    """
    q = (request.GET.get("q") or "").strip()
    filas: list[dict] = []

    # --- Emitidas por ventanilla ---
    vent = BustaCardVentanilla.objects.all()
    if q:
        vent = vent.filter(
            Q(dni__icontains=q) | Q(nombre__icontains=q) | Q(codigo__icontains=q)
        )
    for v in vent[:1000]:
        filas.append({
            "codigo": v.codigo,
            "nombre": v.nombre,
            "dni": v.dni,
            "fecha_emision": v.fecha_emision,
            "fecha_vencimiento": v.fecha_vencimiento,
            "vigente": v.vigente,
            "origen": "Ventanilla",
            "emitido_por": v.emitido_por or "—",
        })

    # --- Emitidas por el app ---
    tarjetas = TarjetaCiudadana.objects.select_related("ciudadano").all()
    if q:
        tarjetas = tarjetas.filter(
            Q(ciudadano__dni__icontains=q)
            | Q(ciudadano__nombres__icontains=q)
            | Q(ciudadano__apellido_paterno__icontains=q)
            | Q(codigo__icontains=q)
        )
    for t in tarjetas[:1000]:
        ciu = t.ciudadano
        nombre = getattr(ciu, "nombre_completo", None) or getattr(ciu, "nombres", "")
        filas.append({
            "codigo": t.codigo,
            "nombre": nombre,
            "dni": getattr(ciu, "dni", ""),
            "fecha_emision": t.fecha_emision,
            "fecha_vencimiento": t.fecha_vencimiento,
            "vigente": t.vigente,
            "origen": "App",
            "emitido_por": "—",
        })

    filas.sort(key=lambda f: f["fecha_emision"], reverse=True)

    total = len(filas)
    vigentes = sum(1 for f in filas if f["vigente"])

    paginator = Paginator(filas, 30)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "ventanilla/historial.html",
        {
            "page": page,
            "q": q,
            "total": total,
            "vigentes": vigentes,
            "vencidas": total - vigentes,
            "logo": _logo_data_uri(),
        },
    )
