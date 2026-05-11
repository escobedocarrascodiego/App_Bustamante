from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView


def health(_request):
    return JsonResponse({"status": "ok", "service": "busta-api"})


api_v1 = [
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("ciudadanos/", include("apps.ciudadanos.urls")),
    path("deudas/", include("apps.deudas.urls")),
    path("tramites/", include("apps.tramites.urls")),
    path("tarjetas/", include("apps.tarjetas.urls")),
    path("catalogos/", include("apps.catalogos.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health),
    path("api/v1/", include((api_v1, "v1"))),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
