from django.urls import path

from .views import GerenciasView, HistorialView, MensajeView, NuevaSesionView

urlpatterns = [
    path("gerencias/", GerenciasView.as_view(), name="chatbot-gerencias"),
    path("sesion/nueva/", NuevaSesionView.as_view(), name="chatbot-sesion-nueva"),
    path("mensaje/", MensajeView.as_view(), name="chatbot-mensaje"),
    path("sesion/historial/", HistorialView.as_view(), name="chatbot-sesion-historial"),
]
