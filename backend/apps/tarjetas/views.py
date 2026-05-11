from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.deudas.services import EstadoBustaCard, comprobar_deuda

from .models import Beneficio, TarjetaCiudadana, UsoBeneficio
from .serializers import BeneficioSerializer, TarjetaSerializer, UsoBeneficioSerializer


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
        return Response(TarjetaSerializer(tarjeta).data)

    def post(self, request):
        if hasattr(request.user, "tarjeta"):
            return Response(
                {"detail": "Ya cuenta con tarjeta ciudadana."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cntrcod = request.user.cntr_cod
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

        # Sincronizar flag en ciudadano
        if not request.user.es_propietario:
            request.user.es_propietario = True
            request.user.save(update_fields=["es_propietario"])

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
