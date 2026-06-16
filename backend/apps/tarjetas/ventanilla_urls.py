"""Rutas del modulo de ventanilla (generacion manual de BustaCard)."""
from django.urls import path

from . import ventanilla

urlpatterns = [
    path("", ventanilla.buscar_view, name="ventanilla_buscar"),
    path("historial/", ventanilla.historial_view, name="ventanilla_historial"),
    path("<int:cntrcod>/", ventanilla.bustacard_view, name="ventanilla_bustacard"),
    path(
        "<int:cntrcod>/pdf/",
        ventanilla.bustacard_pdf_view,
        name="ventanilla_bustacard_pdf",
    ),
]
