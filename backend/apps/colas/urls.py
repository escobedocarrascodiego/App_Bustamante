"""Rutas del gestor de turnos/colas."""
from django.urls import path

from . import views

urlpatterns = [
    # Pantallas
    path("", views.index_view, name="colas_index"),
    path("kiosko/", views.kiosko_view, name="colas_kiosko"),
    path("tv/", views.tv_view, name="colas_tv"),
    path("ventanilla/", views.ventanilla_view, name="colas_ventanilla"),
    # Endpoints JSON
    path("api/emitir/", views.emitir_endpoint, name="colas_emitir"),
    path("api/buscar-dni/", views.buscar_dni_endpoint, name="colas_buscar_dni"),
    path("api/tv-estado/", views.tv_estado_endpoint, name="colas_tv_estado"),
    path("api/mi-ventanilla/", views.mi_ventanilla_endpoint, name="colas_mi_ventanilla"),
    path("api/abrir/", views.abrir_endpoint, name="colas_abrir"),
    path("api/accion/", views.accion_endpoint, name="colas_accion"),
]
