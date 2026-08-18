from django.contrib import admin

from .models import Servicio, Turno, Ventanilla


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "prefijo", "activo", "orden")
    list_editable = ("orden", "activo")
    search_fields = ("nombre", "prefijo")


@admin.register(Ventanilla)
class VentanillaAdmin(admin.ModelAdmin):
    list_display = ("numero", "nombre", "estado", "operador_actual", "activa")
    list_filter = ("estado", "activa")
    search_fields = ("numero", "nombre")
    filter_horizontal = ("servicios",)
    readonly_fields = ("estado", "operador_actual", "turno_actual", "actualizado_en")


@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):
    list_display = (
        "codigo", "servicio", "estado", "prioritario",
        "ventanilla", "dni", "canal", "creado_en",
    )
    list_filter = ("estado", "prioritario", "canal", "servicio", "fecha")
    search_fields = ("codigo", "dni", "nombre")
    readonly_fields = (
        "creado_en", "llamado_en", "inicio_atencion_en", "fin_atencion_en",
        "veces_llamado", "derivado_de",
    )
    date_hierarchy = "fecha"
