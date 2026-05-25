from datetime import UTC, datetime

from apps.catalog.models import Attribute, AttributeValue, ValueType
from apps.common.exceptions import NotFoundError
from apps.intelligence.services.lookup import VehicleResolver


class ComparisonBuilder:
    def build(self, vehicles_input: list[dict], attr_keys: list[str]) -> dict:
        resolver = VehicleResolver()
        versions = []
        for idx, v in enumerate(vehicles_input):
            try:
                version = resolver.resolve(v["brand"], v["model"], v["version"])
            except NotFoundError as exc:
                raise NotFoundError(exc.detail, resource=exc.resource, index=idx) from None
            versions.append(version)

        version_ids = [v.id for v in versions]

        # Single query for all AttributeValues across all versions + requested attrs
        qs = AttributeValue.objects.filter(
            version__id__in=version_ids,
            attribute__key__in=attr_keys,
        ).select_related("attribute__category")

        # Build lookup: (version_id, attr_key) → AttributeValue
        av_map: dict[tuple[int, str], AttributeValue] = {}
        for av in qs:
            av_map[(av.version_id, av.attribute.key)] = av

        # All known attribute keys
        known_keys = set(Attribute.objects.filter(key__in=attr_keys).values_list("key", flat=True))

        vehicles_out = []
        for v in versions:
            vehicles_out.append(
                {
                    "brand": v.model.brand.slug,
                    "model": v.model.slug,
                    "version": v.slug,
                    "display_name": v.name,
                    "model_year": v.model_year,
                }
            )

        matrix = []
        missing = []

        for key in attr_keys:
            if key not in known_keys:
                missing.append(key)
                continue

            av_sample = next(
                (av_map.get((vid, key)) for vid in version_ids if av_map.get((vid, key))),
                None,
            )
            if av_sample is None:
                attr = Attribute.objects.select_related("category").get(key=key)
            else:
                attr = av_sample.attribute

            values = []
            for version in versions:
                av = av_map.get((version.id, key))
                values.append(_render_value(av) if av else None)

            matrix.append(
                {
                    "attribute": {
                        "key": attr.key,
                        "label": attr.label,
                        "unit": attr.unit,
                        "value_type": attr.value_type,
                    },
                    "values": values,
                }
            )

        return {
            "vehicles": vehicles_out,
            "requested_at": datetime.now(tz=UTC).isoformat(),
            "matrix": matrix,
            "missing_attributes": missing,
        }


def _render_value(av: AttributeValue):
    if av.attribute.value_type == ValueType.BOOLEAN:
        return av.boolean_value
    if av.attribute.value_type == ValueType.NUMERIC:
        return float(av.numeric_value)
    return av.text_value
