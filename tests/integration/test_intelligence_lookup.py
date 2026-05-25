import pytest

LOOKUP_URL = "/api/v1/intelligence/lookup/"


def _payload(**kwargs):
    base = {
        "brand": "Ford",
        "model": "Ranger",
        "version": "XLT 3.0L V6 AT 26MY",
        "attributes": ["Potência"],
    }
    base.update(kwargs)
    return base


@pytest.mark.django_db
class TestLookupAnonymous:
    def test_anonymous_401(self, api_client, seeded_catalog):
        resp = api_client.post(LOOKUP_URL, _payload(), format="json")
        assert resp.status_code == 401


@pytest.mark.django_db
class TestLookupHappyPath:
    def test_viewer_200(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.post(LOOKUP_URL, _payload(), format="json")
        assert resp.status_code == 200

    def test_response_shape(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.post(LOOKUP_URL, _payload(), format="json")
        data = resp.json()
        assert "vehicle" in data
        assert "attributes" in data
        assert "missing_attributes" in data
        assert "requested_at" in data
        assert "request_id" in data

    def test_vehicle_block(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.post(LOOKUP_URL, _payload(), format="json")
        v = resp.json()["vehicle"]
        assert v["brand"] == "ford"
        assert v["model"] == "ranger"
        assert v["version"] == "xlt_3_0l_v6_at_26my"
        assert v["display_name"] == "XLT 3.0L V6 AT 26MY"
        assert v["model_year"] == "26MY"

    def test_numeric_attribute(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.post(LOOKUP_URL, _payload(), format="json")
        data = resp.json()
        potencia = next(a for a in data["attributes"] if a["key"] == "potencia")
        assert potencia["value_type"] == "NUMERIC"
        assert potencia["value"] == 250.0
        assert potencia["unit"] == "cv"
        assert potencia["available"] is True

    def test_portuguese_label_normalized(self, viewer_auth_client, seeded_catalog):
        # "Potência" should normalize to "potencia" key
        resp = viewer_auth_client.post(LOOKUP_URL, _payload(attributes=["Potência"]), format="json")
        data = resp.json()
        assert len(data["attributes"]) == 1
        assert data["attributes"][0]["key"] == "potencia"

    def test_order_preserved(self, viewer_auth_client, seeded_catalog):
        # Request in reverse order: boolean first, then numeric
        resp = viewer_auth_client.post(
            LOOKUP_URL,
            _payload(attributes=["Tração 4x4 (high/low)", "Potência"]),
            format="json",
        )
        data = resp.json()
        keys = [a["key"] for a in data["attributes"]]
        assert keys[0] == "tracao_4x4_high_low"
        assert keys[1] == "potencia"

    def test_duplicate_attribute_appears_twice(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.post(
            LOOKUP_URL,
            _payload(attributes=["Potência", "Potência"]),
            format="json",
        )
        data = resp.json()
        assert len(data["attributes"]) == 2
        assert all(a["key"] == "potencia" for a in data["attributes"])

    def test_unknown_attribute_in_missing(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.post(
            LOOKUP_URL,
            _payload(attributes=["Potência", "attribute_that_does_not_exist"]),
            format="json",
        )
        data = resp.json()
        assert "attribute_that_does_not_exist" in data["missing_attributes"]
        keys = [a["key"] for a in data["attributes"]]
        assert "attribute_that_does_not_exist" not in keys

    def test_boolean_true_attribute(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.post(
            LOOKUP_URL,
            _payload(attributes=["Tração 4x4 (high/low)"]),
            format="json",
        )
        data = resp.json()
        attr = data["attributes"][0]
        assert attr["value_type"] == "BOOLEAN"
        assert attr["value"] is True
        assert attr["available"] is True


@pytest.mark.django_db
class TestLookupNotFound:
    def test_brand_not_found_404(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.post(
            LOOKUP_URL,
            _payload(brand="NonExistentBrand"),
            format="json",
        )
        assert resp.status_code == 404
        data = resp.json()
        assert data["error"]["code"] == "NOT_FOUND"
        assert data["error"]["details"]["resource"] == "brand"

    def test_version_not_found_404(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.post(
            LOOKUP_URL,
            _payload(version="NonExistentVersion"),
            format="json",
        )
        assert resp.status_code == 404
        data = resp.json()
        assert data["error"]["code"] == "NOT_FOUND"
        assert data["error"]["details"]["resource"] == "version"


@pytest.mark.django_db
class TestLookupValidation:
    def test_missing_brand_400(self, viewer_auth_client, seeded_catalog):
        payload = _payload()
        del payload["brand"]
        resp = viewer_auth_client.post(LOOKUP_URL, payload, format="json")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_empty_attributes_list_400(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.post(
            LOOKUP_URL,
            _payload(attributes=[]),
            format="json",
        )
        assert resp.status_code == 400

    def test_too_many_attributes_400(self, viewer_auth_client, seeded_catalog):
        attrs = [f"attr_{i}" for i in range(101)]
        resp = viewer_auth_client.post(LOOKUP_URL, _payload(attributes=attrs), format="json")
        assert resp.status_code == 400
