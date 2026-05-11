from rest_framework import serializers

from .models import Deuda, Pago


class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = ["id", "deuda", "monto", "fecha", "medio", "numero_operacion"]
        read_only_fields = ["id", "fecha"]


class DeudaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    pagos = PagoSerializer(many=True, read_only=True)

    class Meta:
        model = Deuda
        fields = [
            "id",
            "tipo",
            "tipo_display",
            "concepto",
            "anio",
            "periodo",
            "monto",
            "interes",
            "descuento",
            "total",
            "fecha_emision",
            "fecha_vencimiento",
            "estado",
            "estado_display",
            "codigo_referencia",
            "pagos",
        ]
