"""
API del gestor de turnos para el APP movil (JWT, ciudadano autenticado).
Va bajo /api/v1/colas/. Distinta de las vistas server-rendered (kiosko/tv/
ventanillero) que viven en views.py.

Flujo en el app:
  GET  estado/        -> como van las colas (monitor)
  GET  mi-turno/      -> mi turno activo de hoy + posicion (o null)
  POST pedir-turno/   -> reserva un turno (RESERVADO, "en camino")
  POST ya-llegue/     -> check-in: la reserva entra a la fila activa
  POST cancelar/      -> cancela mi turno activo
"""
from __future__ import annotations

from django.db.models import Avg
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Servicio, Turno

# Estados que cuentan como "turno activo" del ciudadano.
ACTIVOS = [
    Turno.Estado.RESERVADO,
    Turno.Estado.EN_ESPERA,
    Turno.Estado.LLAMADO,
    Turno.Estado.EN_ATENCION,
]

ATENCION_DEFAULT_SEG = 300  # 5 min si aun no hay datos del dia


def _tiempo_estimado_min(servicio: Servicio, en_espera: int) -> int:
    """Estimacion simple: en_espera x promedio de atencion del dia (o 5 min)."""
    if en_espera <= 0:
        return 0
    prom = (
        Turno.objects.filter(
            servicio=servicio,
            fecha=timezone.localdate(),
            estado=Turno.Estado.ATENDIDO,
            inicio_atencion_en__isnull=False,
            fin_atencion_en__isnull=False,
        )
        .count()
    )
    # Promedio real si hay suficientes atendidos; si no, default.
    seg = ATENCION_DEFAULT_SEG
    if prom >= 3:
        atendidos = Turno.objects.filter(
            servicio=servicio,
            fecha=timezone.localdate(),
            estado=Turno.Estado.ATENDIDO,
            inicio_atencion_en__isnull=False,
            fin_atencion_en__isnull=False,
        )
        total = 0
        n = 0
        for t in atendidos:
            s = t.atencion_segundos
            if s and s > 0:
                total += s
                n += 1
        if n:
            seg = total / n
    return max(1, round(en_espera * seg / 60))


def _turno_payload(turno: Turno) -> dict:
    data = {
        "codigo": turno.codigo,
        "servicio": turno.servicio.nombre,
        "servicio_id": turno.servicio_id,
        "estado": turno.estado,
        "estado_label": turno.get_estado_display(),
        "prioritario": turno.prioritario,
        "ventanilla": turno.ventanilla.numero if turno.ventanilla_id else None,
    }
    if turno.estado == Turno.Estado.EN_ESPERA:
        data["personas_adelante"] = services.personas_adelante(turno)
    else:
        data["personas_adelante"] = None
    return data


class EstadoColasView(APIView):
    """GET /api/v1/colas/estado/ — monitor de colas por servicio."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        hoy = timezone.localdate()
        servicios = Servicio.objects.filter(activo=True).order_by("orden", "nombre")
        data = []
        for s in servicios:
            en_espera = Turno.objects.filter(
                servicio=s, fecha=hoy, estado=Turno.Estado.EN_ESPERA
            ).count()
            data.append({
                "id": s.id,
                "nombre": s.nombre,
                "en_espera": en_espera,
                "tiempo_estimado_min": _tiempo_estimado_min(s, en_espera),
            })
        return Response({"colas": data})


class MiTurnoView(APIView):
    """GET /api/v1/colas/mi-turno/ — turno activo del ciudadano hoy."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        turno = (
            Turno.objects.filter(
                ciudadano=request.user,
                fecha=timezone.localdate(),
                estado__in=ACTIVOS,
            )
            .select_related("servicio", "ventanilla")
            .order_by("-creado_en")
            .first()
        )
        if not turno:
            return Response({"turno": None})
        return Response({"turno": _turno_payload(turno)})


class PedirTurnoView(APIView):
    """POST /api/v1/colas/pedir-turno/ — reserva (RESERVADO, en camino)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Un solo turno activo por ciudadano.
        existente = (
            Turno.objects.filter(
                ciudadano=request.user,
                fecha=timezone.localdate(),
                estado__in=ACTIVOS,
            )
            .select_related("servicio", "ventanilla")
            .first()
        )
        if existente:
            return Response(
                {"detail": "Ya tienes un turno activo.", "turno": _turno_payload(existente)},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            servicio_id = int(request.data.get("servicio_id"))
        except (TypeError, ValueError):
            return Response({"detail": "servicio_id invalido."}, status=400)
        servicio = Servicio.objects.filter(id=servicio_id, activo=True).first()
        if not servicio:
            return Response({"detail": "Servicio no encontrado."}, status=404)

        prioritario = bool(request.data.get("prioritario"))
        dni = (getattr(request.user, "dni", "") or "").strip()
        nombre = (getattr(request.user, "nombre_completo", "") or "").strip()

        turno = services.emitir_turno(
            servicio,
            prioritario=prioritario,
            dni=dni,
            canal=Turno.Canal.APP,
            ciudadano=request.user,
            en_cola=False,  # queda RESERVADO hasta el "Ya llegué"
        )
        # Completar nombre desde el perfil si el padron no lo trajo.
        if not turno.nombre and nombre:
            turno.nombre = nombre
            turno.save(update_fields=["nombre"])
        return Response({"turno": _turno_payload(turno)}, status=status.HTTP_201_CREATED)


class YaLlegueView(APIView):
    """POST /api/v1/colas/ya-llegue/ — check-in: entra a la fila activa."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        turno = Turno.objects.filter(
            ciudadano=request.user,
            fecha=timezone.localdate(),
            estado=Turno.Estado.RESERVADO,
        ).first()
        if not turno:
            return Response(
                {"detail": "No tienes una reserva pendiente de confirmar."},
                status=409,
            )
        services.check_in(turno)
        turno.refresh_from_db()
        return Response({"turno": _turno_payload(turno)})


class CancelarTurnoView(APIView):
    """POST /api/v1/colas/cancelar/ — cancela el turno activo del ciudadano."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        turno = Turno.objects.filter(
            ciudadano=request.user,
            fecha=timezone.localdate(),
            estado__in=[Turno.Estado.RESERVADO, Turno.Estado.EN_ESPERA],
        ).first()
        if not turno:
            return Response({"detail": "No tienes un turno cancelable."}, status=409)
        turno.estado = Turno.Estado.CANCELADO
        turno.save(update_fields=["estado"])
        return Response({"ok": True})
