import pytest
from django.utils import timezone
from freezegun import freeze_time

from apps.accounts.models import AuditLog

LOGIN_URL = "/api/v1/auth/login/"
REFRESH_URL = "/api/v1/auth/refresh/"
LOGOUT_URL = "/api/v1/auth/logout/"

PASSWORD = "Sup3rStrongPass!!!2024"


def _login(client, user):
    return client.post(
        LOGIN_URL,
        {"username": user.username, "password": PASSWORD},
        content_type="application/json",
    )


@pytest.mark.django_db
class TestLogin:
    def test_valid_login_returns_tokens_and_role(self, client, viewer_user):
        resp = _login(client, viewer_user)
        assert resp.status_code == 200
        data = resp.json()
        assert "access" in data
        assert "refresh" in data
        assert data["expires_in"] == 900

        # Decode without verification to check role claim
        import base64
        import json

        payload_b64 = data["access"].split(".")[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.b64decode(payload_b64))
        assert payload["role"] == "VIEWER"

    def test_wrong_password_returns_401(self, client, viewer_user):
        resp = client.post(
            LOGIN_URL,
            {"username": viewer_user.username, "password": "wrongpassword"},
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_unknown_user_returns_401(self, client):
        resp = client.post(
            LOGIN_URL,
            {"username": "nobody", "password": "anypassword"},
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_no_user_enumeration(self, client, viewer_user):
        resp_wrong = client.post(
            LOGIN_URL,
            {"username": viewer_user.username, "password": "wrongpassword"},
            content_type="application/json",
        )
        resp_no_user = client.post(
            LOGIN_URL,
            {"username": "nobody_here", "password": "wrongpassword"},
            content_type="application/json",
        )
        # Compare error block only; request_id is unique per-request
        assert resp_wrong.json()["error"] == resp_no_user.json()["error"]

    def test_audit_log_login_ok(self, client, viewer_user):
        _login(client, viewer_user)
        assert AuditLog.objects.filter(event=AuditLog.Event.LOGIN_OK).exists()

    def test_audit_log_login_fail(self, client, viewer_user):
        client.post(
            LOGIN_URL,
            {"username": viewer_user.username, "password": "bad"},
            content_type="application/json",
        )
        assert AuditLog.objects.filter(event=AuditLog.Event.LOGIN_FAIL).exists()


@pytest.mark.django_db
class TestRefresh:
    def test_refresh_returns_new_access(self, client, viewer_user):
        tokens = _login(client, viewer_user).json()
        resp = client.post(
            REFRESH_URL, {"refresh": tokens["refresh"]}, content_type="application/json"
        )
        assert resp.status_code == 200
        assert "access" in resp.json()
        assert resp.json()["expires_in"] == 900

    def test_refresh_rotates_old_token_blacklisted(self, client, viewer_user):
        tokens = _login(client, viewer_user).json()
        refresh = tokens["refresh"]

        resp1 = client.post(REFRESH_URL, {"refresh": refresh}, content_type="application/json")
        assert resp1.status_code == 200

        # Old refresh must now be blacklisted
        resp2 = client.post(REFRESH_URL, {"refresh": refresh}, content_type="application/json")
        assert resp2.status_code == 401

    def test_audit_log_refresh_ok(self, client, viewer_user):
        tokens = _login(client, viewer_user).json()
        client.post(REFRESH_URL, {"refresh": tokens["refresh"]}, content_type="application/json")
        assert AuditLog.objects.filter(event=AuditLog.Event.REFRESH_OK).exists()


@pytest.mark.django_db
class TestLogout:
    def test_logout_blacklists_refresh(self, client, viewer_user):
        tokens = _login(client, viewer_user).json()
        access = tokens["access"]
        refresh = tokens["refresh"]

        resp = client.post(
            LOGOUT_URL,
            {"refresh": refresh},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )
        assert resp.status_code == 204

        # Refresh token must now be blacklisted
        resp2 = client.post(REFRESH_URL, {"refresh": refresh}, content_type="application/json")
        assert resp2.status_code == 401

    def test_audit_log_logout(self, client, viewer_user):
        tokens = _login(client, viewer_user).json()
        client.post(
            LOGOUT_URL,
            {"refresh": tokens["refresh"]},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}",
        )
        assert AuditLog.objects.filter(event=AuditLog.Event.LOGOUT).exists()

    def test_logout_requires_auth(self, client):
        resp = client.post(LOGOUT_URL, {"refresh": "any"}, content_type="application/json")
        assert resp.status_code == 401


@pytest.mark.django_db
class TestExpiredToken:
    def test_expired_access_token_returns_401(self, client, api_client, viewer_user):
        tokens = _login(client, viewer_user).json()
        access = tokens["access"]

        future = timezone.now() + timezone.timedelta(minutes=16)
        with freeze_time(future):
            api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
            # Logout endpoint requires auth — expired token must yield 401
            resp = api_client.post(LOGOUT_URL, {"refresh": tokens["refresh"]})
            assert resp.status_code == 401


@pytest.mark.django_db
class TestLoginThrottle:
    def test_sixth_login_attempt_returns_429(self, client):
        payload = {"username": "throttle_test", "password": "bad"}
        for _ in range(5):
            client.post(LOGIN_URL, payload, content_type="application/json")

        resp = client.post(LOGIN_URL, payload, content_type="application/json")
        assert resp.status_code == 429
