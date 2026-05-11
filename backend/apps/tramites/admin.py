from django.contrib import admin

from .models import AreaMunicipal, Expediente, SeguimientoExpediente, TipoTramite


@admin.register(AreaMunicipal)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "siglas", "responsable")
    search_fields = ("nombre", "siglas")


@admin.register(TipoTramite)
class TipoTramiteAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "area", "costo", "dias_habiles", "activo")
    list_filter = ("area", "activo")
    search_fields = ("codigo", "nombre")


class SeguimientoInline(admin.TabularInline):
    model = SeguimientoExpediente
    extra = 0
    readonly_fields = ("fecha",)


@admin.register(Expediente)
class ExpedienteAdmin(admin.ModelAdmin):
    list_display = ("numero", "tipo", "ciudadano", "estado", "fecha_ingreso")
    list_filter = ("estado", "tipo")
    search_fields = ("numero", "ciudadano__dni", "asunto")
    inlines = [SeguimientoInline]
