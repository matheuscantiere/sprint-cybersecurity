"""Comprehensive security tests — covers spec 05 controls."""

import hashlib
import hmac
import io
import json
import logging
import time
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.utils import timezone
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken

LOOKUP_URL = "/api/v1/intelligence/lookup/"

_SIMPLE_LOOKUP = {
    "brand": "Ford",
    "model": "Ranger",
    "version": "XLT 3.0L V6 AT 26MY",
    "attributes": ["Potência"],
}


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture
def admin_auth_client(api_client, db):
    from tests.factories import UserFactory

    user = UserFactory(role="ADMIN")
    token = RefreshToken.for_user(user).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


# ── Security Headers ────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSecurityHeaders:
    def test_x_content_type_options_nosniff(self, api_client):
        resp = api_client.get("/health/")
        assert resp["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options_deny(self, api_client):
        resp = api_client.get("/health/")
        assert resp["X-Frame-Options"] == "DENY"

    def test_referrer_policy(self, api_client):
        resp = api_client.get("/health/")
        assert resp["Referrer-Policy"] == "same-origin"

    def test_permissions_policy(self, api_client):
        resp = api_client.get("/health/")
        assert "Permissions-Policy" in resp

    def test_server_header_hides_stack(self, api_client):
        resp = api_client.get("/health/")
        server = resp.get("Server", "")
        assert "Python" not in server
        assert "CPython" not in server
        assert "WSGIServer" not in server
        assert "gunicorn" not in server
        assert server == "fordspy"

    def test_x_request_id_present(self, api_client):
        resp = api_client.get("/health/")
        assert "X-Request-ID" in resp

    def test_x_request_id_echoed_from_client_header(self, api_client):
        custom_rid = "my-custom-request-id-abc123"
        resp = api_client.get("/health/", HTTP_X_REQUEST_ID=custom_rid)
        assert resp["X-Request-ID"] == custom_rid

    def test_request_id_in_body_matches_header(self, api_client):
        resp = api_client.post(
            LOOKUP_URL,
            {"brand": "Unknown", "model": "X", "version": "X", "attributes": ["a"]},
            format="json",
        )
        resp.json()
        rid_header = resp["X-Request-ID"]
        assert rid_header is not None


# ── Input Validation / SQL Injection ──────────────────────────────────────────


@pytest.mark.django_db
class TestInputValidation:
    def test_sql_injection_brand_rejected_400(self, auth_client, seeded_catalog):
        payload = {
            "brand": "Ford';DROP TABLE accounts_user;--",
            "model": "Ranger",
            "version": "XLT 3.0L V6 AT 26MY",
            "attributes": ["potencia"],
        }
        resp = auth_client.post(LOOKUP_URL, payload, format="json")
        assert resp.status_code == 400

    def test_user_table_survives_injection_attempt(self, auth_client, seeded_catalog):
        from apps.accounts.models import User

        payload = {
            "brand": "Ford';DROP TABLE accounts_user;--",
            "model": "Ranger",
            "version": "XLT 3.0L V6 AT 26MY",
            "attributes": ["potencia"],
        }
        auth_client.post(LOOKUP_URL, payload, format="json")
        assert User.objects.exists()

    def test_semicolon_in_model_rejected_400(self, auth_client, seeded_catalog):
        payload = {
            "brand": "Ford",
            "model": "Ranger;rm -rf /",
            "version": "X",
            "attributes": ["a"],
        }
        resp = auth_client.post(LOOKUP_URL, payload, format="json")
        assert resp.status_code == 400

    def test_attributes_101_items_400(self, auth_client):
        payload = {
            "brand": "Ford",
            "model": "Ranger",
            "version": "XLT",
            "attributes": [f"attr{i}" for i in range(101)],
        }
        resp = auth_client.post(LOOKUP_URL, payload, format="json")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_empty_attributes_400(self, auth_client):
        payload = {
            "brand": "Ford",
            "model": "Ranger",
            "version": "XLT",
            "attributes": [],
        }
        resp = auth_client.post(LOOKUP_URL, payload, format="json")
        assert resp.status_code == 400

    def test_request_body_too_large_413(self, api_client):
        big_body = b"x" * (1_048_577)
        resp = api_client.post(
            LOOKUP_URL,
            big_body,
            content_type="application/json",
        )
        assert resp.status_code == 413
        data = resp.json()
        assert data["error"]["code"] == "PAYLOAD_TOO_LARGE"


# ── 404 Routing ────────────────────────────────────────────────────────────────


class TestUnknownRoute:
    @override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
    def test_unknown_route_returns_json_envelope(self, api_client):
        resp = api_client.get("/api/v1/this-does-not-exist/")
        assert resp.status_code == 404
        data = resp.json()
        assert data["error"]["code"] == "NOT_FOUND"
        assert "request_id" in data


# ── OpenAPI Docs Protection ────────────────────────────────────────────────────


class TestOpenApiDocsProtection:
    """SpectacularAPIView.permission_classes is a class attribute fixed at import time.
    patch.object is required; override_settings cannot retroactively change class attributes."""

    def test_schema_unauthenticated_returns_401(self, api_client):
        # DRF raises NotAuthenticated (401) when JWT auth is configured and no token is sent
        with patch.object(SpectacularAPIView, "permission_classes", [IsAdminUser]):
            resp = api_client.get("/api/schema/")
        assert resp.status_code == 401

    def test_docs_unauthenticated_returns_401(self, api_client):
        with patch.object(SpectacularSwaggerView, "permission_classes", [IsAdminUser]):
            resp = api_client.get("/api/docs/")
        assert resp.status_code == 401

    def test_schema_regular_user_returns_403(self, auth_client):
        with patch.object(SpectacularAPIView, "permission_classes", [IsAdminUser]):
            resp = auth_client.get("/api/schema/")
        assert resp.status_code == 403

    @pytest.mark.django_db
    def test_schema_staff_user_returns_200(self, api_client):
        from tests.factories import UserFactory

        user = UserFactory(role="ADMIN", is_staff=True)
        token = RefreshToken.for_user(user).access_token
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        with patch.object(SpectacularAPIView, "permission_classes", [IsAdminUser]):
            resp = api_client.get("/api/schema/")
        assert resp.status_code == 200

    def test_prod_settings_configure_openapi_auth(self):
        from config.settings import prod

        spectacular = prod.SPECTACULAR_SETTINGS
        assert spectacular.get("SERVE_PUBLIC") is False
        assert "rest_framework.permissions.IsAdminUser" in spectacular.get("SERVE_PERMISSIONS", [])
        assert "rest_framework_simplejwt.authentication.JWTAuthentication" in spectacular.get(
            "SERVE_AUTHENTICATION", []
        )


# ── JWT Error Sanitization ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestJwtErrorSanitization:
    def test_invalid_token_details_empty(self, api_client):
        api_client.credentials(HTTP_AUTHORIZATION="Bearer invalid.token.here")
        resp = api_client.get("/health/")
        assert resp.status_code == 401
        data = resp.json()
        assert data["error"]["details"] == {}

    def test_invalid_token_no_token_class_leak(self, api_client):
        api_client.credentials(HTTP_AUTHORIZATION="Bearer invalid.token.here")
        resp = api_client.get("/health/")
        body = resp.content.decode()
        assert "token_class" not in body
        assert "token_type" not in body
        assert "token_not_valid" not in body
        assert "AccessToken" not in body

    def test_invalid_token_generic_message(self, api_client):
        api_client.credentials(HTTP_AUTHORIZATION="Bearer invalid.token.here")
        resp = api_client.get("/health/")
        data = resp.json()
        assert data["error"]["message"] == (
            "Authentication credentials were not provided or are invalid."
        )

    def test_expired_token_details_empty(self, api_client):
        from freezegun import freeze_time

        user = __import__("tests.factories", fromlist=["UserFactory"]).UserFactory()
        with freeze_time("2020-01-01"):
            token = str(RefreshToken.for_user(user).access_token)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        resp = api_client.get("/health/")
        assert resp.status_code == 401
        assert resp.json()["error"]["details"] == {}


# ── 500 / Error Handling ───────────────────────────────────────────────────────


@pytest.mark.django_db
class TestErrorHandling:
    def test_500_no_traceback_in_body(self, api_client):
        resp = api_client.get("/__debug__/error/")
        assert resp.status_code == 500
        body = resp.content.decode()
        assert "Traceback" not in body
        assert "RuntimeError" not in body
        assert "Exception" not in body

    def test_500_has_json_envelope(self, api_client):
        resp = api_client.get("/__debug__/error/")
        assert resp.status_code == 500
        data = resp.json()
        assert data["error"]["code"] == "INTERNAL_ERROR"
        assert "request_id" in data

    def test_400_error_has_request_id(self, auth_client):
        resp = auth_client.post(LOOKUP_URL, {"brand": ""}, format="json")
        assert "request_id" in resp.json()

    def test_401_error_has_request_id(self, api_client):
        resp = api_client.post(LOOKUP_URL, _SIMPLE_LOOKUP, format="json")
        assert resp.status_code == 401
        assert "request_id" in resp.json()

    def test_403_error_has_request_id(self, viewer_auth_client, seeded_catalog):
        resp = viewer_auth_client.post(
            "/api/v1/intelligence/insights/",
            {
                "vehicles": [
                    {"brand": "Ford", "model": "Ranger", "version": "XLT 3.0L V6 AT 26MY"},
                    {"brand": "Ford", "model": "Ranger", "version": "XLT 3.0L V6 AT 26MY"},
                ],
                "attributes": ["potencia"],
            },
            format="json",
        )
        assert resp.status_code == 403
        assert "request_id" in resp.json()

    def test_error_envelope_never_leaks_openai(self, auth_client, seeded_catalog):
        from apps.intelligence.services.insights import InsightsUpstreamError

        with patch("apps.intelligence.views.get_default_client") as mock:
            mock.return_value.generate.side_effect = InsightsUpstreamError("fail")
            resp = auth_client.post(
                "/api/v1/intelligence/insights/",
                {
                    "vehicles": [
                        {"brand": "Ford", "model": "Ranger", "version": "XLT 3.0L V6 AT 26MY"},
                        {"brand": "Ford", "model": "Ranger", "version": "XLT 3.0L V6 AT 26MY"},
                    ],
                    "attributes": ["potencia"],
                },
                format="json",
            )
        assert "OpenAI" not in resp.content.decode()
        assert "openai" not in resp.content.decode().lower()


# ── SensitiveDataFilter ────────────────────────────────────────────────────────


class TestSensitiveDataFilter:
    def _make_record(self, msg, args=()):
        return logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg=msg,
            args=args,
            exc_info=None,
        )

    def test_redacts_password(self):
        from apps.common.logging import SensitiveDataFilter

        f = SensitiveDataFilter()
        record = self._make_record("User set password=secret123 ok")
        f.filter(record)
        assert "secret123" not in record.msg
        assert "[REDACTED]" in record.msg

    def test_redacts_token(self):
        from apps.common.logging import SensitiveDataFilter

        f = SensitiveDataFilter()
        record = self._make_record("Using token=abc.def.ghi for request")
        f.filter(record)
        assert "abc.def.ghi" not in record.msg
        assert "[REDACTED]" in record.msg

    def test_redacts_api_key(self):
        from apps.common.logging import SensitiveDataFilter

        f = SensitiveDataFilter()
        record = self._make_record("api_key=sk-very-secret-value present")
        f.filter(record)
        assert "sk-very-secret-value" not in record.msg
        assert "[REDACTED]" in record.msg

    def test_passes_normal_messages(self):
        from apps.common.logging import SensitiveDataFilter

        f = SensitiveDataFilter()
        record = self._make_record("User logged in successfully")
        f.filter(record)
        assert record.msg == "User logged in successfully"

    def test_redacts_in_args(self):
        from apps.common.logging import SensitiveDataFilter

        f = SensitiveDataFilter()
        record = self._make_record("Result: %s", ("password=hunter2",))
        f.filter(record)
        assert "hunter2" not in record.msg
        assert "[REDACTED]" in record.msg


# ── Retention / Anonymization Commands ────────────────────────────────────────


@pytest.mark.django_db
class TestRetentionCommands:
    def test_prune_old_audit_logs_deleted(self):
        from django.core.management import call_command

        from apps.accounts.models import AuditLog, User

        user = User.objects.create_user(username="u1", password="testpass12345!")
        old = AuditLog.objects.create(event="LOGIN_OK", user=user)
        old.timestamp = timezone.now() - timedelta(days=181)
        old.save(update_fields=["timestamp"])

        call_command("prune_audit_logs", stdout=io.StringIO())
        assert not AuditLog.objects.filter(pk=old.pk).exists()

    def test_prune_keeps_recent_audit_logs(self):
        from django.core.management import call_command

        from apps.accounts.models import AuditLog, User

        user = User.objects.create_user(username="u2", password="testpass12345!")
        recent = AuditLog.objects.create(event="LOGIN_OK", user=user)
        recent.timestamp = timezone.now() - timedelta(days=179)
        recent.save(update_fields=["timestamp"])

        call_command("prune_audit_logs", stdout=io.StringIO())
        assert AuditLog.objects.filter(pk=recent.pk).exists()

    def test_anonymize_old_inactive_users(self):
        from django.core.management import call_command

        from apps.accounts.models import User

        user = User.objects.create_user(username="inactive_old", password="testpass12345!")
        user.is_active = False
        user.date_joined = timezone.now() - timedelta(days=366)
        user.save(update_fields=["is_active", "date_joined"])

        call_command("anonymize_inactive_users", stdout=io.StringIO())
        user.refresh_from_db()
        assert user.username == f"deleted_{user.pk}"
        assert user.email == ""

    def test_anonymize_keeps_active_users(self):
        from django.core.management import call_command

        from apps.accounts.models import User

        user = User.objects.create_user(
            username="active_user_keep",
            password="testpass12345!",
            email="keep@example.com",
        )

        call_command("anonymize_inactive_users", stdout=io.StringIO())
        user.refresh_from_db()
        assert user.username == "active_user_keep"

    def test_anonymize_skips_recent_inactive_users(self):
        from django.core.management import call_command

        from apps.accounts.models import User

        user = User.objects.create_user(
            username="inactive_recent",
            password="testpass12345!",
        )
        user.is_active = False
        user.date_joined = timezone.now() - timedelta(days=100)
        user.save(update_fields=["is_active", "date_joined"])

        call_command("anonymize_inactive_users", stdout=io.StringIO())
        user.refresh_from_db()
        assert user.username == "inactive_recent"


# ── HMAC Middleware ────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestHmacMiddleware:
    SECRET = "test-hmac-secret-key"

    @pytest.fixture(autouse=True)
    def service_client(self, db):
        from apps.accounts.models import ServiceClient

        return ServiceClient.objects.create(
            name="test-service", hmac_secret=self.SECRET, is_active=True
        )

    def _make_signature(self, body: bytes, ts: int | None = None) -> tuple[str, str]:
        if ts is None:
            ts = int(time.time())
        sig = hmac.new(self.SECRET.encode(), body, hashlib.sha256).hexdigest()
        return f"sha256={sig}", str(ts)

    @override_settings(HMAC_VERIFICATION_ENABLED=True)
    def test_valid_signature_passes_to_view(self, api_client):
        body = json.dumps({"brand": "Ford"}).encode()
        sig, ts = self._make_signature(body)
        resp = api_client.generic(
            "GET",
            "/health/",
            data=body,
            content_type="application/json",
            HTTP_X_SIGNATURE=sig,
            HTTP_X_SIGNATURE_TIMESTAMP=ts,
        )
        assert resp.status_code != 401

    @override_settings(HMAC_VERIFICATION_ENABLED=True)
    def test_invalid_signature_returns_401(self, api_client):
        body = b'{"brand": "Ford"}'
        ts = int(time.time())
        resp = api_client.generic(
            "GET",
            "/health/",
            data=body,
            content_type="application/json",
            HTTP_X_SIGNATURE="sha256=badbadbadbad",
            HTTP_X_SIGNATURE_TIMESTAMP=str(ts),
        )
        assert resp.status_code == 401

    @override_settings(HMAC_VERIFICATION_ENABLED=True)
    def test_old_timestamp_rejected(self, api_client):
        body = b'{"brand": "Ford"}'
        old_ts = int(time.time()) - 400
        sig, _ = self._make_signature(body, ts=old_ts)
        resp = api_client.generic(
            "GET",
            "/health/",
            data=body,
            content_type="application/json",
            HTTP_X_SIGNATURE=sig,
            HTTP_X_SIGNATURE_TIMESTAMP=str(old_ts),
        )
        assert resp.status_code == 401

    @override_settings(HMAC_VERIFICATION_ENABLED=True)
    def test_tampered_body_rejected(self, api_client):
        original_body = b'{"brand": "Ford"}'
        tampered_body = b'{"brand": "Toyota"}'
        sig, ts = self._make_signature(original_body)
        resp = api_client.generic(
            "GET",
            "/health/",
            data=tampered_body,
            content_type="application/json",
            HTTP_X_SIGNATURE=sig,
            HTTP_X_SIGNATURE_TIMESTAMP=ts,
        )
        assert resp.status_code == 401

    @override_settings(HMAC_VERIFICATION_ENABLED=True)
    def test_missing_x_signature_prefix_rejected(self, api_client):
        body = b'{"brand": "Ford"}'
        ts = int(time.time())
        sig_hex = hmac.new(self.SECRET.encode(), body, hashlib.sha256).hexdigest()
        resp = api_client.generic(
            "GET",
            "/health/",
            data=body,
            content_type="application/json",
            HTTP_X_SIGNATURE=sig_hex,  # missing "sha256=" prefix
            HTTP_X_SIGNATURE_TIMESTAMP=str(ts),
        )
        assert resp.status_code == 401
