from django.urls import path

from .views import CheckDniView, LoginView, PerfilView, RegisterView

urlpatterns = [
    path("check-dni/", CheckDniView.as_view(), name="ciudadano-check-dni"),
    path("login/", LoginView.as_view(), name="ciudadano-login"),
    path("register/", RegisterView.as_view(), name="ciudadano-register"),
    path("perfil/", PerfilView.as_view(), name="ciudadano-perfil"),
]
