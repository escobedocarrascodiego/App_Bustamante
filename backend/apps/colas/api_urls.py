"""Rutas de la API del app movil (JWT) para turnos. Bajo /api/v1/colas/."""
from django.urls import path

from . import api_app

urlpatterns = [
    path("estado/", api_app.EstadoColasView.as_view(), name="colas_app_estado"),
    path("mi-turno/", api_app.MiTurnoView.as_view(), name="colas_app_mi_turno"),
    path("pedir-turno/", api_app.PedirTurnoView.as_view(), name="colas_app_pedir"),
    path("ya-llegue/", api_app.YaLlegueView.as_view(), name="colas_app_ya_llegue"),
    path("cancelar/", api_app.CancelarTurnoView.as_view(), name="colas_app_cancelar"),
]
