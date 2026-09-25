from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.common.views import ForceErrorView, health_view

handler404 = "apps.common.views.custom_404_view"

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("django_prometheus.urls")),  # exposes /metrics
    path("health/", health_view, name="health"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/catalog/", include("apps.catalog.urls")),
    path("api/v1/intelligence/", include("apps.intelligence.urls")),
]

if settings.DEBUG:
    urlpatterns += [
        path("__debug__/error/", ForceErrorView.as_view(), name="debug_error"),
    ]
