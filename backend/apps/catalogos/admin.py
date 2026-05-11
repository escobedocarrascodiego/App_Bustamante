from django.contrib import admin

from .models import Contacto, LugarInteres, Noticia


@admin.register(Noticia)
class NoticiaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "fecha_publicacion", "destacada", "publicada")
    list_filter = ("destacada", "publicada")
    search_fields = ("titulo",)


@admin.register(LugarInteres)
class LugarAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "direccion", "telefono")
    list_filter = ("tipo",)
    search_fields = ("nombre", "direccion")


@admin.register(Contacto)
class ContactoAdmin(admin.ModelAdmin):
    list_display = ("area", "responsable", "telefono", "email")
    search_fields = ("area", "responsable")
