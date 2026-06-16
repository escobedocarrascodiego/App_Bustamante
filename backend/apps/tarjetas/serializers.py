from rest_framework import serializers

from .models import Beneficio, TarjetaCiudadana, UsoBeneficio


class BeneficioSerializer(serializers.ModelSerializer):
    categoria_display = serializers.CharField(source="get_categoria_display", read_only=True)

    class Meta:
        model = Beneficio
        fields = [
            "id",
            "nombre",
            "descripcion",
            "categoria",
            "categoria_display",
            "lugar",
            "direccion",
            "activo",
            "gratuito",
            "horario",
            "imagen",
        ]


class TarjetaSerializer(serializers.ModelSerializer):
    vigente = serializers.ReadOnlyField()
    dni = serializers.CharField(source="ciudadano.dni", read_only=True)
    nombre_completo = serializers.CharField(
        source="ciudadano.nombre_completo", read_only=True
    )

    class Meta:
        model = TarjetaCiudadana
        fields = [
            "codigo",
            "uuid",
            "dni",
            "nombre_completo",
            "fecha_emision",
            "fecha_vencimiento",
            "activa",
            "bloqueada",
            "motivo_bloqueo",
            "vigente",
        ]
        read_only_fields = fields


class UsoBeneficioSerializer(serializers.ModelSerializer):
    beneficio_nombre = serializers.CharField(source="beneficio.nombre", read_only=True)

    class Meta:
        model = UsoBeneficio
        fields = ["id", "tarjeta", "beneficio", "beneficio_nombre", "fecha", "observacion"]
        read_only_fields = ["id", "fecha", "tarjeta"]
