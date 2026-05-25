import pytest
from django.core.management import call_command

from apps.catalog.models import (
    Attribute,
    AttributeCategory,
    AttributeValue,
    Brand,
    ValueType,
    VehicleModel,
    Version,
)

FIXTURE = "tests/importer/fixtures/tiny_catalog.xlsx"


@pytest.mark.django_db
class TestImportTiny:
    def test_creates_expected_counts(self):
        call_command("import_catalog", FIXTURE, verbosity=0)
        assert Brand.objects.count() == 1
        assert VehicleModel.objects.count() == 1
        assert Version.objects.count() == 1
        assert AttributeCategory.objects.count() == 1
        assert Attribute.objects.count() == 2
        assert AttributeValue.objects.count() == 2

    def test_idempotent(self):
        call_command("import_catalog", FIXTURE, verbosity=0)
        call_command("import_catalog", FIXTURE, verbosity=0)
        assert Brand.objects.count() == 1
        assert VehicleModel.objects.count() == 1
        assert Version.objects.count() == 1
        assert Attribute.objects.count() == 2
        assert AttributeValue.objects.count() == 2

    def test_potencia_is_numeric(self):
        call_command("import_catalog", FIXTURE, verbosity=0)
        attr = Attribute.objects.get(key="potencia")
        assert attr.value_type == ValueType.NUMERIC

    def test_potencia_unit_is_cv(self):
        call_command("import_catalog", FIXTURE, verbosity=0)
        attr = Attribute.objects.get(key="potencia")
        assert attr.unit == "cv"

    def test_boolean_attribute_type(self):
        call_command("import_catalog", FIXTURE, verbosity=0)
        attr = Attribute.objects.get(key="tracao_4x4_high_low")
        assert attr.value_type == ValueType.BOOLEAN

    def test_boolean_value_stored_correctly(self):
        call_command("import_catalog", FIXTURE, verbosity=0)
        attr = Attribute.objects.get(key="tracao_4x4_high_low")
        av = AttributeValue.objects.get(attribute=attr)
        assert av.boolean_value is True
        assert av.is_available is True

    def test_numeric_value_stored_correctly(self):
        call_command("import_catalog", FIXTURE, verbosity=0)
        attr = Attribute.objects.get(key="potencia")
        av = AttributeValue.objects.get(attribute=attr)
        assert float(av.numeric_value) == 250.0
        assert av.is_available is True

    def test_category_name(self):
        call_command("import_catalog", FIXTURE, verbosity=0)
        cat = AttributeCategory.objects.get(slug="engine_and_transmission")
        assert cat.name == "Engine & Transmission"

    def test_version_name(self):
        call_command("import_catalog", FIXTURE, verbosity=0)
        version = Version.objects.get(slug="xlt_3_0l_v6_at_26my")
        assert version.name == "XLT 3.0L V6 AT 26MY"

    def test_unknown_label_does_not_crash(self):
        # tiny fixture has "Tração 4x4 (high/low)" which is not in UNIT_MAP — no crash
        call_command("import_catalog", FIXTURE, verbosity=0)
        assert Attribute.objects.count() == 2


class TestValueTypeResolution:
    """Unit tests for resolve_value_types — no DB required."""

    def _make_data(self, values: dict):
        from apps.catalog.management.commands.import_catalog import (
            ImportData,
            RawAttribute,
            resolve_value_types,
        )

        data = ImportData(
            version_names=list(values.keys()),
            version_slugs=list(values.keys()),
            attributes=[
                RawAttribute(
                    label="Test",
                    key="test",
                    category_slug="cat",
                    category_name="Cat",
                    values=values,
                )
            ],
        )
        return resolve_value_types(data)

    def test_numeric_wins_over_boolean(self):
        data = self._make_data({"v1": 250.0, "v2": "X"})
        assert data.attributes[0].value_type == ValueType.NUMERIC

    def test_all_x_is_boolean(self):
        data = self._make_data({"v1": "X", "v2": "X"})
        assert data.attributes[0].value_type == ValueType.BOOLEAN

    def test_x_and_zero_is_boolean(self):
        data = self._make_data({"v1": "X", "v2": "0"})
        assert data.attributes[0].value_type == ValueType.BOOLEAN

    def test_pure_numeric_is_numeric(self):
        data = self._make_data({"v1": 250.0, "v2": 300.0})
        assert data.attributes[0].value_type == ValueType.NUMERIC
