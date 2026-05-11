from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Ciudadano


@admin.register(Ciudadano)
class CiudadanoAdmin(UserAdmin):
    list_display = ("dni", "nombre_completo", "email", "celular", "verificado", "is_staff")
    list_filter = ("verificado", "is_staff", "is_active")
    search_fields = ("dni", "nombres", "apellido_paterno", "apellido_materno", "email")
    ordering = ("apellido_paterno", "apellido_materno")

    fieldsets = (
        (None, {"fields": ("dni", "password")}),
        ("Datos personales", {
            "fields": (
                "nombres", "apellido_paterno", "apellido_materno",
                "email", "celular", "direccion", "fecha_nacimiento",
            )
        }),
        ("Enlaces externos", {
            "fields": ("cod_pro", "cntr_cod", "es_propietario", "fecha_ultima_sync"),
        }),
        ("Estado", {"fields": ("is_active", "verificado", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Fechas", {"fields": ("last_login", "fecha_registro")}),
    )
    readonly_fields = ("fecha_registro", "last_login", "fecha_ultima_sync")

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("dni", "nombres", "apellido_paterno", "apellido_materno", "password1", "password2"),
        }),
    )
