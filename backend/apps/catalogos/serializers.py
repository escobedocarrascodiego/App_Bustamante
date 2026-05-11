from rest_framework import serializers

from .models import Contacto, LugarInteres, Noticia


class NoticiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Noticia
        fields = [
            "id",
            "titulo",
            "resumen",
            "contenido",
            "imagen",
            "url_fuente",
            "fecha_publicacion",
            "destacada",
        ]


class LugarSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = LugarInteres
        fields = [
            "id",
            "nombre",
            "tipo",
            "tipo_display",
            "direccion",
            "latitud",
            "longitud",
            "telefono",
            "horario",
            "descripcion",
            "imagen",
        ]


class ContactoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contacto
        fields = ["id", "area", "responsable", "telefono", "whatsapp", "email", "horario", "orden"]
