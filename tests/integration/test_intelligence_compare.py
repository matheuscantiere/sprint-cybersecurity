import pytest

from apps.catalog.models import (
    Attribute,
    AttributeCategory,
    AttributeValue,
    Brand,
    ValueType,
    VehicleModel,
    Version,
)

COMPARE_URL = "/api/v1/intelligence/compare/"


@pytest.fixture
def multi_version_catalog(db):
    brand = Brand.objects.create(slug="ford", name="Ford")
    model = VehicleModel.objects.create(
        brand=brand, slug="ranger", name="Ranger", model_year="26MY"
    )
    v1 = Version.objects.create(
        model=model,
        slug="xlt_3_0l_v6_at_26my",
        name="XLT 3.0L V6 AT 26MY",
        model_year="26MY",
    )
    v2 = Version.objects.create(
        model=model,
        slug="limited_3_0l_v6_26my",
        name="Limited 3.0L V6 26MY",
        model_year="26MY",
    )
    v3 = Version.objects.create(
        model=model,
        slug="limited_plus_3_0l_v6_26my",
        name="Limited + 3.0L V6 26MY",
        model_year="26MY",
    )

    cat = AttributeCategory.objects.create(slug="engine", name="Engine", display_order=0)
    cat_safety = AttributeCategory.objects.create(slug="safety", name="Safety", display_order=1)

    attr_pot = Attribute.objects.create(
        key="potencia",
        label="Potência",
        value_type=ValueType.NUMERIC,
        unit="cv",
        category=cat,
    )
    attr_cam = Attribute.objects.create(
        key="camera_360_graus",
        label="Câmera 360 graus",
        value_type=ValueType.BOOLEAN,
        unit=None,
        category=cat_safety,
    )

    # All versions have potencia
    AttributeValue.objects.create(
        version=v1, attribute=attr_pot, numeric_value=250.0, is_available=True
    )
    AttributeValue.objects.create(
        version=v2, attribute=attr_pot, numeric_value=250.0, is_available=True
    )
    AttributeValue.objects.create(
        version=v3, attribute=attr_pot, numeric_value=250.0, is_available=True
    )

    # Only limited_plus has camera 360
    AttributeValue.objects.create(
        version=v1, attribute=attr_cam, boolean_value=False, is_available=False
    )
    AttributeValue.objects.create(
        version=v2, attribute=attr_cam, boolean_value=False, is_available=False
    )
    AttributeValue.objects.create(
        version=v3, attribute=attr_cam, boolean_value=True, is_available=True
    )

    return {"brand": brand, "model": model, "v1": v1, "v2": v2, "v3": v3}


def _vehicles():
    return [
        {"brand": "Ford", "model": "Ranger", "version": "XLT 3.0L V6 AT 26MY"},
        {"brand": "Ford", "model": "Ranger", "version": "Limited 3.0L V6 26MY"},
        {"brand": "Ford", "model": "Ranger", "version": "Limited + 3.0L V6 26MY"},
    ]


@pytest.mark.django_db
class TestCompareAnonymous:
    def test_anonymous_401(self, api_client, multi_version_catalog):
        resp = api_client.post(
            COMPARE_URL,
            {"vehicles": _vehicles()[:2], "attributes": ["Potência"]},
            format="json",
        )
        assert resp.status_code == 401


@pytest.mark.django_db
class TestCompareHappyPath:
    def test_3_vehicles_200(self, viewer_auth_client, multi_version_catalog):
        resp = viewer_auth_client.post(
            COMPARE_URL,
            {"vehicles": _vehicles(), "attributes": ["Potência"]},
            format="json",
        )
        assert resp.status_code == 200

    def test_response_shape(self, viewer_auth_client, multi_version_catalog):
        resp = viewer_auth_client.post(
            COMPARE_URL,
            {"vehicles": _vehicles(), "attributes": ["Potência"]},
            format="json",
        )
        data = resp.json()
        assert "vehicles" in data
        assert "matrix" in data
        assert "missing_attributes" in data
        assert "requested_at" in data
        assert "request_id" in data

    def test_vehicles_count_matches_input(self, viewer_auth_client, multi_version_catalog):
        resp = viewer_auth_client.post(
            COMPARE_URL,
            {"vehicles": _vehicles(), "attributes": ["Potência"]},
            format="json",
        )
        assert len(resp.json()["vehicles"]) == 3

    def test_matrix_values_index_alignment(self, viewer_auth_client, multi_version_catalog):
        resp = viewer_auth_client.post(
            COMPARE_URL,
            {"vehicles": _vehicles(), "attributes": ["Potência"]},
            format="json",
        )
        row = resp.json()["matrix"][0]
        assert row["attribute"]["key"] == "potencia"
        assert row["values"] == [250.0, 250.0, 250.0]

    def test_mixed_boolean_values(self, viewer_auth_client, multi_version_catalog):
        resp = viewer_auth_client.post(
            COMPARE_URL,
            {"vehicles": _vehicles(), "attributes": ["Câmera 360 graus"]},
            format="json",
        )
        row = resp.json()["matrix"][0]
        assert row["attribute"]["key"] == "camera_360_graus"
        assert row["values"] == [False, False, True]

    def test_attribute_order_preserved(self, viewer_auth_client, multi_version_catalog):
        resp = viewer_auth_client.post(
            COMPARE_URL,
            {
                "vehicles": _vehicles()[:2],
                "attributes": ["Câmera 360 graus", "Potência"],
            },
            format="json",
        )
        keys = [r["attribute"]["key"] for r in resp.json()["matrix"]]
        assert keys == ["camera_360_graus", "potencia"]

    def test_unknown_attribute_in_missing(self, viewer_auth_client, multi_version_catalog):
        resp = viewer_auth_client.post(
            COMPARE_URL,
            {"vehicles": _vehicles()[:2], "attributes": ["Potência", "nonexistent"]},
            format="json",
        )
        data = resp.json()
        assert "nonexistent" in data["missing_attributes"]
        keys = [r["attribute"]["key"] for r in data["matrix"]]
        assert "nonexistent" not in keys


@pytest.mark.django_db
class TestCompareValidation:
    def test_one_vehicle_400(self, viewer_auth_client, multi_version_catalog):
        resp = viewer_auth_client.post(
            COMPARE_URL,
            {"vehicles": [_vehicles()[0]], "attributes": ["Potência"]},
            format="json",
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_six_vehicles_400(self, viewer_auth_client, multi_version_catalog):
        six = (_vehicles() * 2)[:6]
        resp = viewer_auth_client.post(
            COMPARE_URL,
            {"vehicles": six, "attributes": ["Potência"]},
            format="json",
        )
        assert resp.status_code == 400

    def test_unknown_vehicle_404_with_index(self, viewer_auth_client, multi_version_catalog):
        vehicles = [
            {"brand": "Ford", "model": "Ranger", "version": "XLT 3.0L V6 AT 26MY"},
            {"brand": "Ford", "model": "Ranger", "version": "Nonexistent Version 99MY"},
        ]
        resp = viewer_auth_client.post(
            COMPARE_URL,
            {"vehicles": vehicles, "attributes": ["Potência"]},
            format="json",
        )
        assert resp.status_code == 404
        data = resp.json()
        assert data["error"]["code"] == "NOT_FOUND"
        assert data["error"]["details"]["resource"] == "version"
        assert data["error"]["details"]["index"] == 1
