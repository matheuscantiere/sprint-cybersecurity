"""OpenAPI schema tests — validates schema accuracy and completeness."""

import pytest


@pytest.fixture
def schema(api_client):
    resp = api_client.get("/api/schema/?format=json")
    assert resp.status_code == 200
    return resp.json()


class TestSchemaBasics:
    def test_schema_endpoint_200(self, api_client):
        resp = api_client.get("/api/schema/")
        assert resp.status_code == 200

    def test_schema_title(self, schema):
        assert schema["info"]["title"] == "FordSpy API"

    def test_schema_version(self, schema):
        assert schema["info"]["version"] == "0.1.0"

    def test_swagger_ui_200(self, api_client):
        resp = api_client.get("/api/docs/")
        assert resp.status_code == 200


class TestOperationIds:
    """Every shipped endpoint must appear in the schema."""

    EXPECTED_PATHS = [
        "/api/v1/auth/login/",
        "/api/v1/auth/refresh/",
        "/api/v1/auth/logout/",
        "/api/v1/catalog/brands/",
        "/api/v1/catalog/brands/{brand_slug}/models/",
        "/api/v1/catalog/brands/{brand_slug}/models/{model_slug}/versions/",
        "/api/v1/catalog/attributes/",
        "/api/v1/intelligence/lookup/",
        "/api/v1/intelligence/compare/",
        "/api/v1/intelligence/insights/",
    ]

    def test_all_expected_paths_present(self, schema):
        paths = schema.get("paths", {})
        missing = [p for p in self.EXPECTED_PATHS if p not in paths]
        assert missing == [], f"Missing paths in schema: {missing}"

    def test_operation_count_at_least_10(self, schema):
        paths = schema.get("paths", {})
        ops = sum(len(methods) for methods in paths.values())
        assert ops >= 10, f"Expected ≥10 operations, got {ops}"


class TestIntelligenceExamples:
    """Intelligence operations must each have at least one request example."""

    INTELLIGENCE_PATHS = [
        "/api/v1/intelligence/lookup/",
        "/api/v1/intelligence/compare/",
        "/api/v1/intelligence/insights/",
    ]

    def _get_examples(self, schema, path):
        op = schema["paths"].get(path, {}).get("post", {})
        content = op.get("requestBody", {}).get("content", {})
        examples = {}
        for _media_type, media_obj in content.items():
            examples.update(media_obj.get("examples", {}))
        return examples

    def test_lookup_has_example(self, schema):
        examples = self._get_examples(schema, "/api/v1/intelligence/lookup/")
        assert len(examples) >= 1, "lookup must have at least one request example"

    def test_compare_has_example(self, schema):
        examples = self._get_examples(schema, "/api/v1/intelligence/compare/")
        assert len(examples) >= 1, "compare must have at least one request example"

    def test_insights_has_example(self, schema):
        examples = self._get_examples(schema, "/api/v1/intelligence/insights/")
        assert len(examples) >= 1, "insights must have at least one request example"


class TestSecuritySchemes:
    def test_bearer_auth_scheme_defined(self, schema):
        schemes = schema.get("components", {}).get("securitySchemes", {})
        assert "BearerAuth" in schemes, f"BearerAuth not found. Schemes: {list(schemes.keys())}"

    def test_bearer_auth_is_http_bearer(self, schema):
        scheme = schema["components"]["securitySchemes"]["BearerAuth"]
        assert scheme["type"] == "http"
        assert scheme["scheme"] == "bearer"

    def test_intelligence_lookup_requires_auth(self, schema):
        op = schema["paths"]["/api/v1/intelligence/lookup/"]["post"]
        security = op.get("security", schema.get("security", []))
        scheme_names = [list(s.keys())[0] for s in security if s]
        assert "BearerAuth" in scheme_names

    def test_catalog_brands_requires_auth(self, schema):
        op = schema["paths"]["/api/v1/catalog/brands/"]["get"]
        security = op.get("security", schema.get("security", []))
        scheme_names = [list(s.keys())[0] for s in security if s]
        assert "BearerAuth" in scheme_names


class TestTags:
    def test_auth_tag_defined(self, schema):
        tag_names = [t["name"] for t in schema.get("tags", [])]
        assert "Auth" in tag_names

    def test_catalog_tag_defined(self, schema):
        tag_names = [t["name"] for t in schema.get("tags", [])]
        assert "Catalog" in tag_names

    def test_intelligence_tag_defined(self, schema):
        tag_names = [t["name"] for t in schema.get("tags", [])]
        assert "Intelligence" in tag_names

    def test_lookup_tagged_intelligence(self, schema):
        op = schema["paths"]["/api/v1/intelligence/lookup/"]["post"]
        assert "Intelligence" in op.get("tags", [])

    def test_login_tagged_auth(self, schema):
        op = schema["paths"]["/api/v1/auth/login/"]["post"]
        assert "Auth" in op.get("tags", [])

    def test_brands_tagged_catalog(self, schema):
        op = schema["paths"]["/api/v1/catalog/brands/"]["get"]
        assert "Catalog" in op.get("tags", [])


class TestJwtExamples:
    """JWT examples must use explicit placeholders, not eyJ… strings that look like real tokens."""

    def test_no_eyj_in_schema(self, schema):
        import json

        raw = json.dumps(schema)
        assert "eyJhbGci" not in raw

    def test_login_example_uses_placeholder(self, schema):
        examples = (
            schema["paths"]["/api/v1/auth/login/"]["post"]
            .get("responses", {})
            .get("200", {})
            .get("content", {})
            .get("application/json", {})
            .get("examples", {})
        )
        for ex in examples.values():
            value = ex.get("value", {})
            assert value.get("access") == "<jwt-access-token>"
            assert value.get("refresh") == "<jwt-refresh-token>"
