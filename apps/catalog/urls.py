from django.urls import path

from apps.catalog.views import (
    AttributeListView,
    BrandListView,
    VehicleModelListView,
    VersionListView,
)

urlpatterns = [
    path("brands/", BrandListView.as_view(), name="catalog-brands"),
    path(
        "brands/<slug:brand_slug>/models/",
        VehicleModelListView.as_view(),
        name="catalog-models",
    ),
    path(
        "brands/<slug:brand_slug>/models/<slug:model_slug>/versions/",
        VersionListView.as_view(),
        name="catalog-versions",
    ),
    path("attributes/", AttributeListView.as_view(), name="catalog-attributes"),
]
