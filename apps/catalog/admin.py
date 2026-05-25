from django.contrib import admin

from .models import (
    Attribute,
    AttributeCategory,
    AttributeValue,
    Brand,
    VehicleModel,
    Version,
)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "created_at")
    search_fields = ("slug", "name")


@admin.register(VehicleModel)
class VehicleModelAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "slug", "model_year")
    list_filter = ("brand",)
    search_fields = ("name", "slug")


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    list_display = ("name", "model", "slug", "model_year")
    list_filter = ("model__brand",)
    search_fields = ("name", "slug")


@admin.register(AttributeCategory)
class AttributeCategoryAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "display_order")
    search_fields = ("slug", "name")


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ("key", "label", "category", "value_type", "unit")
    list_filter = ("value_type", "category")
    search_fields = ("key", "label")


@admin.register(AttributeValue)
class AttributeValueAdmin(admin.ModelAdmin):
    list_display = (
        "version",
        "attribute",
        "is_available",
        "boolean_value",
        "numeric_value",
        "text_value",
    )
    list_filter = ("is_available", "attribute__value_type")
    search_fields = ("version__name", "attribute__key")
