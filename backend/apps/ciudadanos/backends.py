"""
Backend de autenticacion que acepta DNI o username.

Razon de existir:
- El app movil de ciudadanos se autentica por DNI (`USERNAME_FIELD = "dni"`).
- El admin de Django se administra por superusuarios con `username` (ej.
  "admin") + password, sin relacion con DNIs reales.

Este backend recibe el valor del formulario (sea DNI o username) y prueba
ambos campos. El usuario que machee y tenga la password correcta gana.
"""
from __future__ import annotations

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q


class UsernameOrDniBackend(ModelBackend):
    """
    Acepta tanto `username=` (admin login form) como `dni=` (LoginSerializer
    del app movil) en la misma llamada `authenticate()`. Si vienen ambos,
    gana el primero no-nulo. La busqueda final corre sobre los dos campos
    del modelo (`username` y `dni`) con OR, asi cualquiera de los dos
    valores tipeados encuentra al user correcto.
    """

    def authenticate(self, request, username=None, password=None, dni=None, **kwargs):
        UserModel = get_user_model()
        identificador = username or dni
        if not identificador or not password:
            return None
        try:
            user = UserModel.objects.get(
                Q(username=identificador) | Q(dni=identificador)
            )
        except UserModel.DoesNotExist:
            return None
        except UserModel.MultipleObjectsReturned:
            # Caso teorico: alguien tiene username "12345678" y otro su DNI
            # "12345678". Priorizamos username exacto sobre dni.
            user = (
                UserModel.objects.filter(username=identificador).first()
                or UserModel.objects.filter(dni=identificador).first()
            )
            if user is None:
                return None
        if not user.check_password(password):
            return None
        if not self.user_can_authenticate(user):
            return None
        return user
