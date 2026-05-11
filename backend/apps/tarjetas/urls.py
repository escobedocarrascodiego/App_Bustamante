from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import BeneficioViewSet, TarjetaView, UsoBeneficioViewSet

router = DefaultRouter()
router.register(r"beneficios", BeneficioViewSet, basename="beneficio")
router.register(r"usos", UsoBeneficioViewSet, basename="uso-beneficio")

urlpatterns = [
    path("mi-tarjeta/", TarjetaView.as_view(), name="mi-tarjeta"),
]

urlpatterns += router.urls
