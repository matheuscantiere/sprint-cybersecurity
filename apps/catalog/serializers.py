from rest_framework import serializers

from apps.catalog.models import (
    Attribute,
    AttributeCategory,
    Brand,
    VehicleModel,
    Version,
)


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["slug", "name"]


class VehicleModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleModel
        fields = ["slug", "name", "model_year"]


class VersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Version
        fields = ["slug", "name", "model_year"]


class AttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attribute
        fields = ["key", "label", "value_type", "unit"]


class AttributeCategorySerializer(serializers.ModelSerializer):
    attributes = AttributeSerializer(many=True, read_only=True)

    class Meta:
        model = AttributeCategory
        fields = ["slug", "name", "attributes"]


class CatalogAttributesEnvelopeSerializer(serializers.Serializer):
    categories = AttributeCategorySerializer(many=True)
