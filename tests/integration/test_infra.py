import pytest


@pytest.mark.django_db
def test_health(client):
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_debug_off_in_prod_settings():
    from config.settings import prod

    assert prod.DEBUG is False


def test_nginx_prod_conf_suppresses_server_header():
    from pathlib import Path

    conf = (Path(__file__).resolve().parents[2] / "nginx" / "nginx.prod.conf").read_text()
    assert "server_tokens off" in conf
    assert "proxy_hide_header Server" in conf
    assert 'add_header Server "fordspy"' in conf


def test_prod_settings_https_and_hsts():
    from config.settings import prod

    assert prod.SECURE_SSL_REDIRECT is True
    assert prod.SESSION_COOKIE_SECURE is True
    assert prod.CSRF_COOKIE_SECURE is True
    assert prod.SECURE_HSTS_SECONDS == 31_536_000
    assert prod.SECURE_HSTS_INCLUDE_SUBDOMAINS is True
    assert prod.SECURE_HSTS_PRELOAD is True


def test_nginx_prod_conf_port_8000_not_exposed():
    """Port 8000 (WSGI) must not be listed in the nginx upstream or listen directives —
    only nginx handles external traffic."""
    from pathlib import Path

    conf = (Path(__file__).resolve().parents[2] / "nginx" / "nginx.prod.conf").read_text()
    assert "listen 443" in conf
    assert "listen 80" in conf
