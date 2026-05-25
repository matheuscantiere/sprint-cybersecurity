import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.catalog.models import (
    Attribute,
    AttributeCategory,
    AttributeValue,
    Brand,
    ValueType,
    VehicleModel,
    Version,
)
from apps.intelligence.services.lookup import StandardizedResponseBuilder


@pytest.fixture
def catalog_version(db):
    brand = Brand.objects.create(slug="ford", name="Ford")
    model = VehicleModel.objects.create(
        brand=brand, slug="ranger", name="Ranger", model_year="26MY"
    )
    version = Version.objects.create(model=model, slug="xlt", name="XLT", model_year="26MY")
    cat = AttributeCategory.objects.create(slug="engine", name="Engine", display_order=0)
    return version, cat


@pytest.mark.django_db
class TestBuilderStates:
    def test_known_and_present(self, catalog_version):
        version, cat = catalog_version
        attr = Attribute.objects.create(
            key="potencia",
            label="Potência",
            value_type=ValueType.NUMERIC,
            unit="cv",
            category=cat,
        )
        AttributeValue.objects.create(
            version=version, attribute=attr, numeric_value=250.0, is_available=True
        )

        result = StandardizedResponseBuilder().build(version, ["potencia"])
        assert len(result["attributes"]) == 1
        a = result["attributes"][0]
        assert a["key"] == "potencia"
        assert a["value"] == 250.0
        assert a["available"] is True
        assert a["unit"] == "cv"

    def test_known_but_no_value(self, catalog_version):
        version, cat = catalog_version
        Attribute.objects.create(
            key="teto_solar",
            label="Teto Solar",
            value_type=ValueType.BOOLEAN,
            unit=None,
            category=cat,
        )

        result = StandardizedResponseBuilder().build(version, ["teto_solar"])
        assert len(result["attributes"]) == 1
        a = result["attributes"][0]
        assert a["key"] == "teto_solar"
        assert a["value"] is None
        assert a["available"] is False

    def test_unknown_goes_to_missing(self, catalog_version):
        version, _ = catalog_version
        result = StandardizedResponseBuilder().build(version, ["nonexistent_key"])
        assert result["attributes"] == []
        assert "nonexistent_key" in result["missing_attributes"]

    def test_boolean_true_value(self, catalog_version):
        version, cat = catalog_version
        attr = Attribute.objects.create(
            key="tracao",
            label="Tração",
            value_type=ValueType.BOOLEAN,
            unit=None,
            category=cat,
        )
        AttributeValue.objects.create(
            version=version, attribute=attr, boolean_value=True, is_available=True
        )

        result = StandardizedResponseBuilder().build(version, ["tracao"])
        a = result["attributes"][0]
        assert a["value"] is True
        assert a["available"] is True

    def test_boolean_false_value(self, catalog_version):
        version, cat = catalog_version
        attr = Attribute.objects.create(
            key="teto_solar",
            label="Teto Solar",
            value_type=ValueType.BOOLEAN,
            unit=None,
            category=cat,
        )
        AttributeValue.objects.create(
            version=version, attribute=attr, boolean_value=False, is_available=False
        )

        result = StandardizedResponseBuilder().build(version, ["teto_solar"])
        a = result["attributes"][0]
        assert a["value"] is False
        assert a["available"] is False

    def test_order_preserved(self, catalog_version):
        version, cat = catalog_version
        attr_a = Attribute.objects.create(
            key="attr_a",
            label="A",
            value_type=ValueType.BOOLEAN,
            unit=None,
            category=cat,
        )
        attr_b = Attribute.objects.create(
            key="attr_b",
            label="B",
            value_type=ValueType.NUMERIC,
            unit=None,
            category=cat,
        )
        AttributeValue.objects.create(
            version=version, attribute=attr_a, boolean_value=True, is_available=True
        )
        AttributeValue.objects.create(
            version=version, attribute=attr_b, numeric_value=10.0, is_available=True
        )

        result = StandardizedResponseBuilder().build(version, ["attr_b", "attr_a"])
        keys = [a["key"] for a in result["attributes"]]
        assert keys == ["attr_b", "attr_a"]

    def test_single_query_for_many_attributes(self, catalog_version):
        version, cat = catalog_version
        attrs = []
        for i in range(10):
            a = Attribute.objects.create(
                key=f"attr_{i}",
                label=f"Attr {i}",
                value_type=ValueType.BOOLEAN,
                unit=None,
                category=cat,
            )
            AttributeValue.objects.create(
                version=version, attribute=a, boolean_value=True, is_available=True
            )
            attrs.append(f"attr_{i}")

        with CaptureQueriesContext(connection) as ctx:
            StandardizedResponseBuilder().build(version, attrs)

        assert len(ctx.captured_queries) <= 2
