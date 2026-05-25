import pytest

BRANDS_URL = "/api/v1/catalog/brands/"
MODELS_URL = "/api/v1/catalog/brands/ford/models/"
VERSIONS_URL = "/api/v1/catalog/brands/ford/models/ranger/versions/"
ATTRS_URL = "/api/v1/catalog/attributes/"


@pytest.mark.django_db
class TestAnonymousRejected:
    def test_brands_401(self, api_client):
        assert api_client.get(BRANDS_URL).status_code == 401

    def test_models_401(self, api_client):
        assert api_client.get(MODELS_URL).status_code == 401

    def test_versions_401(self, api_client):
        assert api_client.get(VERSIONS_URL).status_code == 401

    def test_attributes_401(self, api_client):
        assert api_client.get(ATTRS_URL).status_code == 401


@pytest.mark.django_db
class TestBrandList:
    def test_viewer_gets_200(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.get(BRANDS_URL)
        assert resp.status_code == 200

    def test_response_shape(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.get(BRANDS_URL)
        data = resp.json()
        assert "results" in data
        brand = data["results"][0]
        assert brand["slug"] == "ford"
        assert brand["name"] == "Ford"


@pytest.mark.django_db
class TestModelList:
    def test_viewer_gets_200(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.get(MODELS_URL)
        assert resp.status_code == 200

    def test_response_shape(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.get(MODELS_URL)
        data = resp.json()
        assert "results" in data
        m = data["results"][0]
        assert m["slug"] == "ranger"
        assert m["name"] == "Ranger"

    def test_unknown_brand_404(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.get("/api/v1/catalog/brands/nonexistent/models/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestVersionList:
    def test_viewer_gets_200(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.get(VERSIONS_URL)
        assert resp.status_code == 200

    def test_response_shape(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.get(VERSIONS_URL)
        data = resp.json()
        assert "results" in data
        v = data["results"][0]
        assert v["slug"] == "xlt_3_0l_v6_at_26my"
        assert v["name"] == "XLT 3.0L V6 AT 26MY"
        assert v["model_year"] == "26MY"

    def test_unknown_model_404(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.get("/api/v1/catalog/brands/ford/models/nonexistent/versions/")
        assert resp.status_code == 404

    def test_unknown_brand_404(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.get("/api/v1/catalog/brands/nonexistent/models/ranger/versions/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestAttributeList:
    def test_viewer_gets_200(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.get(ATTRS_URL)
        assert resp.status_code == 200

    def test_response_has_categories(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.get(ATTRS_URL)
        data = resp.json()
        assert "categories" in data
        cat = next(c for c in data["categories"] if c["slug"] == "engine_and_transmission")
        assert cat["name"] == "Engine & Transmission"
        keys = [a["key"] for a in cat["attributes"]]
        assert "potencia" in keys

    def test_category_filter(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.get(ATTRS_URL + "?category=safety")
        data = resp.json()
        assert len(data["categories"]) == 1
        assert data["categories"][0]["slug"] == "safety"

    def test_category_filter_no_results(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.get(ATTRS_URL + "?category=nonexistent")
        data = resp.json()
        assert data["categories"] == []

    def test_search_filter_by_key(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.get(ATTRS_URL + "?search=potencia")
        data = resp.json()
        all_keys = [a["key"] for cat in data["categories"] for a in cat["attributes"]]
        assert "potencia" in all_keys

    def test_search_filter_case_insensitive(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.get(ATTRS_URL + "?search=Pot%C3%AAncia")
        data = resp.json()
        all_keys = [a["key"] for cat in data["categories"] for a in cat["attributes"]]
        assert "potencia" in all_keys

    def test_attribute_shape(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.get(ATTRS_URL + "?category=engine_and_transmission")
        data = resp.json()
        attr = data["categories"][0]["attributes"][0]
        assert set(attr.keys()) >= {"key", "label", "value_type", "unit"}
        assert attr["value_type"] == "NUMERIC"
        assert attr["unit"] == "cv"
