import logging
from datetime import UTC, datetime

from apps.catalog.models import (
    Attribute,
    AttributeValue,
    Brand,
    ValueType,
    VehicleModel,
    Version,
)
from apps.common.exceptions import NotFoundError

logger = logging.getLogger("apps.intelligence")


class VehicleResolver:
    def resolve(self, brand_slug: str, model_slug: str, version_slug: str) -> Version:
        try:
            brand = Brand.objects.get(slug=brand_slug)
        except Brand.DoesNotExist:
            raise NotFoundError(f"Brand '{brand_slug}' not found.", resource="brand") from None

        try:
            model = VehicleModel.objects.get(brand=brand, slug=model_slug)
        except VehicleModel.DoesNotExist:
            raise NotFoundError(f"Model '{model_slug}' not found.", resource="model") from None

        try:
            version = Version.objects.select_related("model__brand").get(
                model=model, slug=version_slug
            )
        except Version.DoesNotExist:
            raise NotFoundError(
                f"Version '{version_slug}' not found.", resource="version"
            ) from None

        return version


class StandardizedResponseBuilder:
    def build(self, version: Version, attr_keys: list[str]) -> dict:
        # One query: all attribute values for this version + requested keys
        values_qs = AttributeValue.objects.filter(
            version=version, attribute__key__in=attr_keys
        ).select_related("attribute__category")
        value_map: dict[str, AttributeValue] = {av.attribute.key: av for av in values_qs}

        # One query: all known attributes for keys not in value_map
        keys_without_value = [k for k in attr_keys if k not in value_map]
        known_attr_map: dict[str, Attribute] = {}
        if keys_without_value:
            for attr in Attribute.objects.filter(key__in=keys_without_value).select_related(
                "category"
            ):
                known_attr_map[attr.key] = attr

        attributes = []
        missing = []

        for key in attr_keys:
            if key in value_map:
                av = value_map[key]
                attr = av.attribute
                attributes.append(
                    {
                        "key": attr.key,
                        "label": attr.label,
                        "category": attr.category.slug,
                        "value_type": attr.value_type,
                        "value": self._render_value(av),
                        "unit": attr.unit,
                        "available": av.is_available,
                    }
                )
            elif key in known_attr_map:
                attr = known_attr_map[key]
                logger.warning("Known attribute %r has no value for version %s", key, version.slug)
                attributes.append(
                    {
                        "key": attr.key,
                        "label": attr.label,
                        "category": attr.category.slug,
                        "value_type": attr.value_type,
                        "value": None,
                        "unit": attr.unit,
                        "available": False,
                    }
                )
            else:
                missing.append(key)

        v = version
        return {
            "vehicle": {
                "brand": v.model.brand.slug,
                "model": v.model.slug,
                "version": v.slug,
                "display_name": v.name,
                "model_year": v.model_year,
            },
            "requested_at": datetime.now(tz=UTC).isoformat(),
            "attributes": attributes,
            "missing_attributes": missing,
        }

    @staticmethod
    def _render_value(av: AttributeValue):
        if av.attribute.value_type == ValueType.BOOLEAN:
            return av.boolean_value
        if av.attribute.value_type == ValueType.NUMERIC:
            return float(av.numeric_value)
        return av.text_value
