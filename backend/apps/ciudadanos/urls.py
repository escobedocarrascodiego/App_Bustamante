from django.urls import path

from .views import (
    CheckDniView,
    LoginView,
    PerfilView,
    RegisterOmitidoView,
    RegisterView,
    VerificarMpvView,
)

urlpatterns = [
    path("check-dni/", CheckDniView.as_view(), name="ciudadano-check-dni"),
    path("login/", LoginView.as_view(), name="ciudadano-login"),
    path("register/", RegisterView.as_view(), name="ciudadano-register"),
    path(
        "register-omitido/",
        RegisterOmitidoView.as_view(),
        name="ciudadano-register-omitido",
    ),
    path(
        "verificar-mpv/",
        VerificarMpvView.as_view(),
        name="ciudadano-verificar-mpv",
    ),
    path("perfil/", PerfilView.as_view(), name="ciudadano-perfil"),
]
