import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.catalog.models import (
    Attribute,
    AttributeCategory,
    AttributeValue,
    Brand,
    ValueType,
    VehicleModel,
    Version,
)


def make_brand(slug="ford", name="Ford"):
    return Brand.objects.create(slug=slug, name=name)


def make_category(slug="engine", name="Engine", order=0):
    return AttributeCategory.objects.create(slug=slug, name=name, display_order=order)


def make_attr(category, key="potencia", label="Potência", value_type=ValueType.NUMERIC):
    return Attribute.objects.create(category=category, key=key, label=label, value_type=value_type)


@pytest.mark.django_db
class TestBrand:
    def test_create_brand(self):
        brand = make_brand()
        assert brand.pk is not None
        assert brand.slug == "ford"

    def test_duplicate_slug_raises(self):
        make_brand()
        with pytest.raises(IntegrityError):
            make_brand()


@pytest.mark.django_db
class TestVehicleModel:
    def test_create_model(self):
        brand = make_brand()
        vehicle_model = VehicleModel.objects.create(
            brand=brand, slug="ranger", name="Ranger", model_year="26MY"
        )
        assert vehicle_model.pk is not None

    def test_unique_together_brand_slug(self):
        brand = make_brand()
        VehicleModel.objects.create(brand=brand, slug="ranger", name="Ranger")
        with pytest.raises(IntegrityError):
            VehicleModel.objects.create(brand=brand, slug="ranger", name="Ranger Duplicate")

    def test_same_slug_different_brand_allowed(self):
        ford = make_brand(slug="ford", name="Ford")
        gm = make_brand(slug="gm", name="GM")
        VehicleModel.objects.create(brand=ford, slug="ranger", name="Ranger")
        model2 = VehicleModel.objects.create(brand=gm, slug="ranger", name="Ranger GM")
        assert model2.pk is not None


@pytest.mark.django_db
class TestVersion:
    def test_create_version(self):
        brand = make_brand()
        vehicle_model = VehicleModel.objects.create(brand=brand, slug="ranger", name="Ranger")
        version = Version.objects.create(
            model=vehicle_model, slug="xlt", name="XLT 3.0L V6 AT 26MY"
        )
        assert version.pk is not None

    def test_unique_together_model_slug(self):
        brand = make_brand()
        vehicle_model = VehicleModel.objects.create(brand=brand, slug="ranger", name="Ranger")
        Version.objects.create(model=vehicle_model, slug="xlt", name="XLT")
        with pytest.raises(IntegrityError):
            Version.objects.create(model=vehicle_model, slug="xlt", name="XLT Duplicate")


@pytest.mark.django_db
class TestAttribute:
    def test_create_attribute(self):
        category = make_category()
        attr = make_attr(category)
        assert attr.pk is not None
        assert attr.value_type == ValueType.NUMERIC

    def test_duplicate_key_raises(self):
        category = make_category()
        make_attr(category)
        with pytest.raises(IntegrityError):
            make_attr(category)


@pytest.mark.django_db
class TestAttributeValue:
    def _setup(self):
        brand = make_brand()
        vehicle_model = VehicleModel.objects.create(brand=brand, slug="ranger", name="Ranger")
        version = Version.objects.create(model=vehicle_model, slug="xlt", name="XLT")
        category = make_category()
        attr = make_attr(category)
        return version, attr

    def test_create_numeric_value(self):
        version, attr = self._setup()
        av = AttributeValue.objects.create(version=version, attribute=attr, numeric_value=250)
        assert av.pk is not None

    def test_create_boolean_value(self):
        version, attr = self._setup()
        category = make_category(slug="safety", name="Safety")
        bool_attr = make_attr(
            category,
            key="camera_360",
            label="Câmera 360°",
            value_type=ValueType.BOOLEAN,
        )
        av = AttributeValue.objects.create(version=version, attribute=bool_attr, boolean_value=True)
        assert av.boolean_value is True

    def test_two_non_null_values_raises_validation_error(self):
        version, attr = self._setup()
        av = AttributeValue(version=version, attribute=attr, numeric_value=250, boolean_value=True)
        with pytest.raises(ValidationError):
            av.full_clean()

    def test_all_null_values_raises_validation_error(self):
        version, attr = self._setup()
        av = AttributeValue(version=version, attribute=attr)
        with pytest.raises(ValidationError):
            av.full_clean()

    def test_unique_together_version_attribute(self):
        version, attr = self._setup()
        AttributeValue.objects.create(version=version, attribute=attr, numeric_value=250)
        with pytest.raises(IntegrityError):
            AttributeValue.objects.create(version=version, attribute=attr, numeric_value=300)
