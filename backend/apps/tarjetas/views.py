from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.deudas.services import (
    EstadoBustaCard,
    comprobar_deuda,
    obtener_cntrcod_usuario,
)

from .models import Beneficio, TarjetaCiudadana, UsoBeneficio
from .serializers import BeneficioSerializer, TarjetaSerializer, UsoBeneficioSerializer


# Motivo con el que el sistema bloquea automaticamente una tarjeta cuando
# detecta deuda. Lo usamos como "marca" para distinguir un bloqueo AUTOMATICO
# (que se levanta solo al pagar) de uno MANUAL hecho por un administrador.
MOTIVO_BLOQUEO_DEUDA = "Deuda pendiente con la municipalidad"


def sincronizar_bloqueo_por_deuda(user, tarjeta):
    """
    Mantiene el flag `bloqueada` de la tarjeta en sync con la deuda real (SIAP):

      - Si el contribuyente tiene deuda / no es propietario -> bloquea por
        deuda (motivo = MOTIVO_BLOQUEO_DEUDA).
      - Si esta al dia y el bloqueo vigente era POR DEUDA -> lo levanta.
      - Respeta los bloqueos MANUALES (cualquier otro motivo): no los toca.

    Devuelve la verificacion de deuda (o None si no se pudo calcular).
    """
    cntrcod = obtener_cntrcod_usuario(user)
    if not cntrcod:
        return None

    verificacion = comprobar_deuda(cntrcod)
    al_dia = verificacion["estado_busta_card"] == EstadoBustaCard.AL_DIA

    if not al_dia:
        # Solo auto-bloqueamos si no hay ya un bloqueo (manual o por deuda).
        if not tarjeta.bloqueada:
            tarjeta.bloqueada = True
            tarjeta.motivo_bloqueo = MOTIVO_BLOQUEO_DEUDA
            tarjeta.save(update_fields=["bloqueada", "motivo_bloqueo"])
    else:
        # Al dia: si el bloqueo era automatico por deuda, lo levantamos.
        if tarjeta.bloqueada and tarjeta.motivo_bloqueo == MOTIVO_BLOQUEO_DEUDA:
            tarjeta.bloqueada = False
            tarjeta.motivo_bloqueo = ""
            tarjeta.save(update_fields=["bloqueada", "motivo_bloqueo"])

    return verificacion


class BeneficioViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Beneficio.objects.filter(activo=True)
    serializer_class = BeneficioSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ["categoria", "gratuito"]
    search_fields = ["nombre", "lugar"]


class TarjetaView(APIView):
    """Obtiene o emite la tarjeta del ciudadano autenticado."""

    def get(self, request):
        tarjeta = getattr(request.user, "tarjeta", None)
        if not tarjeta:
            return Response(
                {"detail": "Aun no tiene tarjeta ciudadana emitida."},
                status=status.HTTP_404_NOT_FOUND,
            )
        # Sincroniza el bloqueo con la deuda real antes de devolverla, asi
        # `vigente` refleja el estado actual (deuda, vencimiento, bloqueo).
        sincronizar_bloqueo_por_deuda(request.user, tarjeta)
        return Response(TarjetaSerializer(tarjeta).data)

    def post(self, request):
        """
        Emite o RENUEVA la tarjeta:
          - Sin tarjeta -> emite una nueva.
          - Tarjeta VENCIDA (paso el año) -> la renueva para el año actual,
            siempre que el contribuyente este al dia.
          - Tarjeta vigente -> no se re-emite (ya tiene una valida).
        """
        tarjeta = getattr(request.user, "tarjeta", None)
        hoy = timezone.localdate()

        # Si ya tiene una tarjeta y NO esta vencida, no procede re-emitir.
        # (Si esta bloqueada por deuda en un año vigente, se reactiva sola al
        # pagar via sincronizar_bloqueo_por_deuda — no se re-emite.)
        if tarjeta and tarjeta.fecha_vencimiento >= hoy:
            return Response(
                {"detail": "Ya cuentas con una tarjeta vigente para este año."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resolvemos el cntr_cod igual que la consulta de deuda (con fallback
        # por DNI), para no rechazar a quien SI esta en el padron pero aun no
        # tiene el cntr_cod cacheado en su perfil.
        cntrcod = obtener_cntrcod_usuario(request.user)
        if not cntrcod:
            return Response(
                {
                    "detail": "Tu DNI no figura en el padron de contribuyentes. "
                    "Acercate a la municipalidad para regularizar tu inscripcion.",
                    "estado_busta_card": "SIN_CONTRIBUYENTE",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        verificacion = comprobar_deuda(cntrcod)
        estado = verificacion["estado_busta_card"]
        if estado != EstadoBustaCard.AL_DIA:
            return Response(
                {"detail": verificacion["mensaje"], **verificacion},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Sincronizar flags en el ciudadano (cacheamos el cntr_cod resuelto).
        cambios = []
        if request.user.cntr_cod != cntrcod:
            request.user.cntr_cod = cntrcod
            cambios.append("cntr_cod")
        if not request.user.es_propietario:
            request.user.es_propietario = True
            cambios.append("es_propietario")
        if cambios:
            request.user.save(update_fields=cambios)

        if tarjeta:
            # RENOVACION: la tarjeta vencida se reactiva para el ejercicio
            # actual (mismo codigo, nueva emision y vencimiento, desbloqueada).
            tarjeta.fecha_emision = timezone.now()
            tarjeta.fecha_vencimiento = hoy.replace(month=12, day=31)
            tarjeta.activa = True
            tarjeta.bloqueada = False
            tarjeta.motivo_bloqueo = ""
            tarjeta.save(update_fields=[
                "fecha_emision", "fecha_vencimiento",
                "activa", "bloqueada", "motivo_bloqueo",
            ])
            return Response(TarjetaSerializer(tarjeta).data, status=status.HTTP_200_OK)

        tarjeta = TarjetaCiudadana.objects.create(ciudadano=request.user)
        return Response(TarjetaSerializer(tarjeta).data, status=status.HTTP_201_CREATED)


class UsoBeneficioViewSet(viewsets.ModelViewSet):
    serializer_class = UsoBeneficioSerializer
    http_method_names = ["get", "post"]

    def get_queryset(self):
        return UsoBeneficio.objects.filter(tarjeta__ciudadano=self.request.user)

    def perform_create(self, serializer):
        tarjeta = getattr(self.request.user, "tarjeta", None)
        if not tarjeta or not tarjeta.vigente:
            raise permissions.exceptions.PermissionDenied(
                "Tarjeta ciudadana no vigente."
            )
        serializer.save(tarjeta=tarjeta)

    @action(detail=False, methods=["get"])
    def historial(self, request):
        data = UsoBeneficioSerializer(self.get_queryset(), many=True).data
        return Response(data)
