from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    CheckDniSerializer,
    CiudadanoSerializer,
    LoginSerializer,
    RegisterSerializer,
)


class CheckDniView(APIView):
    """
    Paso 1 del login: el ciudadano ingresa solo el DNI y le decimos al
    front si tiene que pedir password, crear cuenta o mandar a MPV.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = CheckDniSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class LoginView(APIView):
    """Login con DNI + contraseña local (ya configurada)."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class RegisterView(APIView):
    """Primera vez en el app: crea la contraseña y emite JWT."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_201_CREATED)


class PerfilView(generics.RetrieveUpdateAPIView):
    serializer_class = CiudadanoSerializer

    def get_object(self):
        return self.request.user
