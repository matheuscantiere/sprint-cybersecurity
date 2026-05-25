from django.core.exceptions import ValidationError
from django.db import models


class ValueType(models.TextChoices):
    BOOLEAN = "BOOLEAN", "Boolean"
    NUMERIC = "NUMERIC", "Numeric"
    TEXT = "TEXT", "Text"


class Brand(models.Model):
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class VehicleModel(models.Model):
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="models")
    slug = models.SlugField(max_length=100, db_index=True)
    name = models.CharField(max_length=120)
    model_year = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("brand", "slug")

    def __str__(self) -> str:
        return f"{self.brand} {self.name}"


class Version(models.Model):
    model = models.ForeignKey(VehicleModel, on_delete=models.PROTECT, related_name="versions")
    slug = models.SlugField(max_length=100, db_index=True)
    name = models.CharField(max_length=160)
    model_year = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("model", "slug")

    def __str__(self) -> str:
        return self.name


class AttributeCategory(models.Model):
    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=80)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order"]

    def __str__(self) -> str:
        return self.name


class Attribute(models.Model):
    category = models.ForeignKey(
        AttributeCategory, on_delete=models.PROTECT, related_name="attributes"
    )
    key = models.SlugField(max_length=100, unique=True, db_index=True)
    label = models.CharField(max_length=200)
    value_type = models.CharField(max_length=10, choices=ValueType.choices)
    unit = models.CharField(max_length=20, null=True, blank=True)  # noqa: DJ001
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.key


class AttributeValue(models.Model):
    version = models.ForeignKey(Version, on_delete=models.CASCADE, related_name="attribute_values")
    attribute = models.ForeignKey(Attribute, on_delete=models.PROTECT, related_name="values")
    boolean_value = models.BooleanField(null=True, blank=True)
    numeric_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    text_value = models.CharField(max_length=200, null=True, blank=True)  # noqa: DJ001
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("version", "attribute")
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        boolean_value__isnull=False,
                        numeric_value__isnull=True,
                        text_value__isnull=True,
                    )
                    | models.Q(
                        boolean_value__isnull=True,
                        numeric_value__isnull=False,
                        text_value__isnull=True,
                    )
                    | models.Q(
                        boolean_value__isnull=True,
                        numeric_value__isnull=True,
                        text_value__isnull=False,
                    )
                ),
                name="catalog_attrvalue_exactly_one_value",
            )
        ]

    def __str__(self) -> str:
        return f"{self.version} / {self.attribute}"

    def clean(self) -> None:
        non_null = sum(
            [
                self.boolean_value is not None,
                self.numeric_value is not None,
                self.text_value is not None,
            ]
        )
        if non_null != 1:
            raise ValidationError(
                "Exactly one of boolean_value, numeric_value, text_value must be non-null."
            )
