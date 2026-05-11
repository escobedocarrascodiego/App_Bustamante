from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AreaViewSet,
    ExpedienteViewSet,
    TipoTramiteViewSet,
    catalogo_formulario,
    detalle_expediente_siap_view,
    mis_expedientes_siap,
    registrar_tramite_externo,
)

router = DefaultRouter()
router.register(r"tipos", TipoTramiteViewSet, basename="tipo-tramite")
router.register(r"areas", AreaViewSet, basename="area")
router.register(r"expedientes", ExpedienteViewSet, basename="expediente")

urlpatterns = [
    path("mis-expedientes-siap/", mis_expedientes_siap, name="mis-expedientes-siap"),
    path(
        "expediente-siap/<int:cod_ing>/",
        detalle_expediente_siap_view,
        name="expediente-siap-detalle",
    ),
    path("catalogo-formulario/", catalogo_formulario, name="catalogo-formulario"),
    path(
        "registrar-tramite-externo/",
        registrar_tramite_externo,
        name="registrar-tramite-externo",
    ),
    *router.urls,
]
