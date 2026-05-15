"""
Serializers expuestos al frontend del chatbot. Mantenemos la superficie
chica: solo lo que necesita el cliente.
"""
from rest_framework import serializers

from .models import Gerencia, MensajeChat


class GerenciaSerializer(serializers.ModelSerializer):
    """Version "lean" de Gerencia para el selector del chat."""

    class Meta:
        model = Gerencia
        fields = ["id", "nombre"]
        read_only_fields = fields


class NuevaSesionRequestSerializer(serializers.Serializer):
    """No recibe body — placeholder por consistencia con DRF."""


class NuevaSesionResponseSerializer(serializers.Serializer):
    sesion_id = serializers.UUIDField()


class MensajeRequestSerializer(serializers.Serializer):
    sesion_id = serializers.UUIDField()
    mensaje = serializers.CharField(max_length=2000, allow_blank=False, trim_whitespace=True)
    gerencia_id = serializers.IntegerField(required=False, allow_null=True)


class MensajeResponseSerializer(serializers.Serializer):
    respuesta = serializers.CharField()
    encontrado = serializers.BooleanField()
    sesion_id = serializers.UUIDField()


class MensajeChatSerializer(serializers.ModelSerializer):
    """Mensaje del historial — version "lean" para el front."""

    class Meta:
        model = MensajeChat
        fields = ["rol", "contenido", "creado_en"]
        read_only_fields = fields


class HistorialResponseSerializer(serializers.Serializer):
    mensajes = MensajeChatSerializer(many=True)
