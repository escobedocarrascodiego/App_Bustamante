from django.contrib import admin

from .models import Deuda, Pago


@admin.register(Deuda)
class DeudaAdmin(admin.ModelAdmin):
    list_display = ("codigo_referencia", "ciudadano", "tipo", "anio", "periodo", "monto", "estado")
    list_filter = ("tipo", "estado", "anio")
    search_fields = ("codigo_referencia", "ciudadano__dni", "concepto")


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("deuda", "monto", "medio", "fecha", "numero_operacion")
    list_filter = ("medio",)
    search_fields = ("numero_operacion", "deuda__codigo_referencia")
