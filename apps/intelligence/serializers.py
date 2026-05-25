import re

from rest_framework import serializers

from apps.common.utils import slugify_attribute

# Whitelist for vehicle identity fields — blocks SQL/command injection characters
_IDENTITY_RE = re.compile(r"^[\w\s\-\+\.]+$")


def _validate_identity(value: str, field_name: str) -> str:
    v = value.strip()
    if not _IDENTITY_RE.match(v):
        raise serializers.ValidationError(f"{field_name} contains disallowed characters.")
    slug = slugify_attribute(v)
    if not slug:
        raise serializers.ValidationError(f"{field_name} is invalid after normalization.")
    return slug


class LookupRequestSerializer(serializers.Serializer):
    brand = serializers.CharField(max_length=100)
    model = serializers.CharField(max_length=100)
    version = serializers.CharField(max_length=100)
    attributes = serializers.ListField(
        child=serializers.CharField(max_length=200),
        min_length=1,
        max_length=100,
    )

    def validate_brand(self, value):
        return _validate_identity(value, "Brand")

    def validate_model(self, value):
        return _validate_identity(value, "Model")

    def validate_version(self, value):
        return _validate_identity(value, "Version")

    def validate_attributes(self, values):
        result = []
        for raw in values:
            slug = slugify_attribute(raw.strip())
            if not slug:
                raise serializers.ValidationError(
                    f"Attribute {raw!r} is invalid after normalization."
                )
            result.append(slug)
        return result


class VehicleResponseSerializer(serializers.Serializer):
    brand = serializers.CharField()
    model = serializers.CharField()
    version = serializers.CharField()
    display_name = serializers.CharField()
    model_year = serializers.CharField()


class AttributeResponseSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    category = serializers.CharField()
    value_type = serializers.CharField()
    value = serializers.JSONField(allow_null=True)
    unit = serializers.CharField(allow_null=True)
    available = serializers.BooleanField()


class LookupResponseSerializer(serializers.Serializer):
    vehicle = VehicleResponseSerializer()
    requested_at = serializers.CharField()
    request_id = serializers.CharField()
    attributes = AttributeResponseSerializer(many=True)
    missing_attributes = serializers.ListField(child=serializers.CharField())


class VehicleInputSerializer(serializers.Serializer):
    brand = serializers.CharField(max_length=100)
    model = serializers.CharField(max_length=100)
    version = serializers.CharField(max_length=100)

    def validate_brand(self, value):
        return _validate_identity(value, "Brand")

    def validate_model(self, value):
        return _validate_identity(value, "Model")

    def validate_version(self, value):
        return _validate_identity(value, "Version")


class CompareRequestSerializer(serializers.Serializer):
    vehicles = serializers.ListField(
        child=VehicleInputSerializer(),
        min_length=2,
        max_length=5,
    )
    attributes = serializers.ListField(
        child=serializers.CharField(max_length=200),
        min_length=1,
        max_length=100,
    )

    def validate_attributes(self, values):
        result = []
        for raw in values:
            slug = slugify_attribute(raw.strip())
            if not slug:
                raise serializers.ValidationError(
                    f"Attribute {raw!r} is invalid after normalization."
                )
            result.append(slug)
        return result


class AttributeMatrixSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    unit = serializers.CharField(allow_null=True)
    value_type = serializers.CharField()


class MatrixRowSerializer(serializers.Serializer):
    attribute = AttributeMatrixSerializer()
    values = serializers.ListField(child=serializers.JSONField(allow_null=True))


class CompareResponseSerializer(serializers.Serializer):
    vehicles = VehicleResponseSerializer(many=True)
    requested_at = serializers.CharField()
    request_id = serializers.CharField()
    matrix = MatrixRowSerializer(many=True)
    missing_attributes = serializers.ListField(child=serializers.CharField())


class InsightsRequestSerializer(serializers.Serializer):
    vehicles = serializers.ListField(
        child=VehicleInputSerializer(),
        min_length=2,
        max_length=5,
    )
    attributes = serializers.ListField(
        child=serializers.CharField(max_length=200),
        min_length=1,
        max_length=100,
    )
    focus = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        default="",
    )

    def validate_attributes(self, values):
        result = []
        for raw in values:
            slug = slugify_attribute(raw.strip())
            if not slug:
                raise serializers.ValidationError(
                    f"Attribute {raw!r} is invalid after normalization."
                )
            result.append(slug)
        return result

    def validate_focus(self, value):
        import re

        if value and not re.fullmatch(r"[A-Za-z0-9 \-]*", value):
            raise serializers.ValidationError(
                "focus contains disallowed characters. Only letters, digits, spaces, hyphens allowed."  # noqa: E501
            )
        return value


class KeyDifferenceSerializer(serializers.Serializer):
    attribute = serializers.CharField()
    winner = serializers.JSONField(required=False)
    values = serializers.JSONField(required=False)


class InsightsResponseSerializer(serializers.Serializer):
    summary = serializers.CharField()
    key_differences = KeyDifferenceSerializer(many=True)
    model = serializers.CharField()
    generated_at = serializers.CharField()
    request_id = serializers.CharField()
