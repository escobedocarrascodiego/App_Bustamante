from rest_framework import permissions, viewsets

from .models import Contacto, LugarInteres, Noticia
from .serializers import ContactoSerializer, LugarSerializer, NoticiaSerializer


class NoticiaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Noticia.objects.filter(publicada=True)
    serializer_class = NoticiaSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ["destacada"]
    search_fields = ["titulo", "resumen"]


class LugarViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LugarInteres.objects.all()
    serializer_class = LugarSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ["tipo"]
    search_fields = ["nombre", "direccion"]


class ContactoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Contacto.objects.all()
    serializer_class = ContactoSerializer
    permission_classes = [permissions.AllowAny]
