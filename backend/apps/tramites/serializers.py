from rest_framework import serializers

from .models import AreaMunicipal, Expediente, SeguimientoExpediente, TipoTramite


class AreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = AreaMunicipal
        fields = ["id", "nombre", "siglas", "responsable"]


class TipoTramiteSerializer(serializers.ModelSerializer):
    area_nombre = serializers.CharField(source="area.nombre", read_only=True)
    requisitos = serializers.SerializerMethodField()

    class Meta:
        model = TipoTramite
        fields = [
            "id",
            "codigo",
            "nombre",
            "descripcion",
            "area",
            "area_nombre",
            "requisitos",
            "costo",
            "dias_habiles",
            "activo",
        ]

    def get_requisitos(self, obj) -> list[str]:
        return obj.requisitos_list


class SeguimientoSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    area_nombre = serializers.CharField(source="area.nombre", read_only=True, default=None)

    class Meta:
        model = SeguimientoExpediente
        fields = ["id", "estado", "estado_display", "comentario", "area", "area_nombre", "fecha"]


class ExpedienteSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source="tipo.nombre", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    seguimientos = SeguimientoSerializer(many=True, read_only=True)

    class Meta:
        model = Expediente
        fields = [
            "id",
            "numero",
            "uuid",
            "tipo",
            "tipo_nombre",
            "asunto",
            "detalle",
            "estado",
            "estado_display",
            "fecha_ingreso",
            "fecha_actualizacion",
            "fecha_estimada",
            "seguimientos",
        ]
        read_only_fields = ["numero", "uuid", "estado", "fecha_ingreso", "fecha_actualizacion"]


class CrearExpedienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expediente
        fields = ["tipo", "asunto", "detalle"]
