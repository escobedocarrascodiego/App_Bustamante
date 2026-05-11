from django.contrib import admin

from .models import Beneficio, TarjetaCiudadana, UsoBeneficio


@admin.register(Beneficio)
class BeneficioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "lugar", "gratuito", "activo")
    list_filter = ("categoria", "activo", "gratuito")
    search_fields = ("nombre", "lugar")


@admin.register(TarjetaCiudadana)
class TarjetaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "ciudadano", "fecha_emision", "fecha_vencimiento", "activa", "bloqueada")
    list_filter = ("activa", "bloqueada")
    search_fields = ("codigo", "ciudadano__dni")


@admin.register(UsoBeneficio)
class UsoBeneficioAdmin(admin.ModelAdmin):
    list_display = ("tarjeta", "beneficio", "fecha")
    list_filter = ("beneficio",)
