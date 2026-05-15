"""Admin Django del chatbot: gestion de Gerencias y FAQs, lectura de sesiones."""
from django.contrib import admin
from django.utils.html import format_html

from .models import ConversacionSesion, Faq, Gerencia, MensajeChat


# ---------------------------------------------------------------------------
# Gerencias
# ---------------------------------------------------------------------------


@admin.register(Gerencia)
class GerenciaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo", "orden")
    list_editable = ("activo", "orden")
    ordering = ("orden", "nombre")
    search_fields = ("nombre", "descripcion")
    list_per_page = 50


# ---------------------------------------------------------------------------
# FAQs
# ---------------------------------------------------------------------------


@admin.action(description="Activar FAQs seleccionadas")
def activar_seleccionadas(modeladmin, request, queryset):
    actualizadas = queryset.update(activo=True)
    modeladmin.message_user(request, f"{actualizadas} FAQ(s) activadas.")


@admin.action(description="Desactivar FAQs seleccionadas")
def desactivar_seleccionadas(modeladmin, request, queryset):
    actualizadas = queryset.update(activo=False)
    modeladmin.message_user(request, f"{actualizadas} FAQ(s) desactivadas.")


@admin.register(Faq)
class FaqAdmin(admin.ModelAdmin):
    list_display = (
        "pregunta_truncada",
        "gerencia",
        "activo",
        "veces_consultada",
        "actualizado_en",
    )
    list_filter = ("gerencia", "activo")
    search_fields = ("pregunta", "respuesta", "keywords")
    list_editable = ("activo",)
    list_per_page = 30
    readonly_fields = ("veces_consultada", "creado_en", "actualizado_en")
    actions = [activar_seleccionadas, desactivar_seleccionadas]
    ordering = ("-veces_consultada", "id")
    fieldsets = (
        ("Información básica", {"fields": ("gerencia", "activo")}),
        ("Contenido", {"fields": ("pregunta", "respuesta", "keywords")}),
        (
            "Estadísticas (solo lectura)",
            {"fields": ("veces_consultada", "creado_en", "actualizado_en")},
        ),
    )

    @admin.display(description="Pregunta")
    def pregunta_truncada(self, obj: Faq) -> str:
        texto = (obj.pregunta or "").strip()
        return texto[:60] + ("…" if len(texto) > 60 else "")


# ---------------------------------------------------------------------------
# Sesiones + mensajes (solo lectura)
# ---------------------------------------------------------------------------


class MensajeChatInline(admin.TabularInline):
    model = MensajeChat
    extra = 0
    can_delete = False
    fields = ("rol", "contenido_corto", "faq_origen", "creado_en")
    readonly_fields = ("rol", "contenido_corto", "faq_origen", "creado_en")
    ordering = ("creado_en",)

    @admin.display(description="Contenido")
    def contenido_corto(self, obj: MensajeChat) -> str:
        texto = (obj.contenido or "").strip()
        if len(texto) <= 200:
            return texto
        return format_html("{} <em>… (truncado)</em>", texto[:200])

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ConversacionSesion)
class ConversacionSesionAdmin(admin.ModelAdmin):
    list_display = (
        "sesion_id",
        "ciudadano",
        "iniciado_en",
        "ultimo_mensaje_en",
        "cantidad_mensajes",
    )
    list_filter = ("iniciado_en",)
    search_fields = ("sesion_id", "ciudadano__dni", "ciudadano__nombres")
    ordering = ("-iniciado_en",)
    list_per_page = 50
    readonly_fields = (
        "sesion_id",
        "ciudadano",
        "iniciado_en",
        "ultimo_mensaje_en",
    )
    inlines = [MensajeChatInline]

    @admin.display(description="Mensajes")
    def cantidad_mensajes(self, obj: ConversacionSesion) -> int:
        return obj.mensajes.count()

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        # Permitimos borrar para limpieza, pero no editar individualmente
        return True

    def has_change_permission(self, request, obj=None):
        return True  # solo navegacion — todos los campos son readonly


# MensajeChat no se expone como modelo independiente en el admin: solo via
# el inline de ConversacionSesion para mantener el contexto.
