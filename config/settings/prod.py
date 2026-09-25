from .base import *  # noqa: F401, F403
from .base import SPECTACULAR_SETTINGS, env

DEBUG = False
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

CRYPTOGRAPHY_KEY = env("CRYPTOGRAPHY_KEY")  # required — raises ImproperlyConfigured if unset

SPECTACULAR_SETTINGS = {
    **SPECTACULAR_SETTINGS,
    "SWAGGER_UI_SETTINGS": {"persistAuthorization": False},
    "SERVE_PUBLIC": False,
    "SERVE_AUTHENTICATION": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAdminUser"],
}
