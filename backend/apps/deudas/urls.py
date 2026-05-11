from rest_framework.routers import DefaultRouter

from .views import DeudaViewSet

router = DefaultRouter()
router.register(r"", DeudaViewSet, basename="deuda")

urlpatterns = router.urls
