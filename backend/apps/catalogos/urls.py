from rest_framework.routers import DefaultRouter

from .views import ContactoViewSet, LugarViewSet, NoticiaViewSet

router = DefaultRouter()
router.register(r"noticias", NoticiaViewSet, basename="noticia")
router.register(r"lugares", LugarViewSet, basename="lugar")
router.register(r"contactos", ContactoViewSet, basename="contacto")

urlpatterns = router.urls
