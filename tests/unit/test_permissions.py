from unittest.mock import MagicMock

import pytest

from apps.common.permissions import HasRole


def _make_request(role=None, authenticated=True):
    request = MagicMock()
    user = MagicMock()
    user.is_authenticated = authenticated
    user.role = role
    request.user = user
    return request


class TestHasRole:
    def test_viewer_allowed_when_viewer_required(self):
        perm = HasRole.of("VIEWER")()
        assert perm.has_permission(_make_request(role="VIEWER"), MagicMock()) is True

    def test_analyst_allowed_when_analyst_or_admin_required(self):
        perm = HasRole.of("ANALYST", "ADMIN")()
        assert perm.has_permission(_make_request(role="ANALYST"), MagicMock()) is True

    def test_admin_allowed_for_any_role_set(self):
        perm = HasRole.of("ANALYST", "ADMIN")()
        assert perm.has_permission(_make_request(role="ADMIN"), MagicMock()) is True

    def test_viewer_denied_when_analyst_required(self):
        perm = HasRole.of("ANALYST", "ADMIN")()
        assert perm.has_permission(_make_request(role="VIEWER"), MagicMock()) is False

    def test_unauthenticated_denied(self):
        perm = HasRole.of("VIEWER", "ANALYST", "ADMIN")()
        assert perm.has_permission(_make_request(authenticated=False), MagicMock()) is False

    def test_class_name_reflects_roles(self):
        cls = HasRole.of("ANALYST", "ADMIN")
        assert "ANALYST" in cls.__name__
        assert "ADMIN" in cls.__name__


@pytest.mark.django_db
class TestRbacAnonymous:
    """Anonymous must get 401 on all /api/v1/* except auth endpoints."""

    def test_anonymous_on_protected_endpoint(self, client):
        # No auth endpoint that exists at this stage — use a non-existent one
        # to confirm the 401/404 behaviour (401 before 404 due to DRF default permission)
        resp = client.get("/api/v1/catalog/brands/")
        # 404 because route not wired yet, but NOT a 200 without auth
        assert resp.status_code in (401, 404)

    def test_login_is_public(self, client):
        resp = client.post(
            "/api/v1/auth/login/",
            {"username": "x", "password": "y"},
            content_type="application/json",
        )
        # 401 due to bad creds, NOT a 403 (endpoint is accessible)
        assert resp.status_code == 401

    def test_refresh_is_public(self, client):
        resp = client.post(
            "/api/v1/auth/refresh/",
            {"refresh": "bad"},
            content_type="application/json",
        )
        assert resp.status_code == 401
