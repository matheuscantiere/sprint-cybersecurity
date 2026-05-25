import hashlib
import hmac as hmac_lib
import logging
import time
import uuid

from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger("apps.common.middleware")

_MAX_BODY = 1_048_576  # 1 MB — mirrors DATA_UPLOAD_MAX_MEMORY_SIZE


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        rid = request.META.get("HTTP_X_REQUEST_ID") or uuid.uuid4().hex
        request.request_id = rid
        response = self.get_response(request)
        response["X-Request-ID"] = rid
        return response


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["Referrer-Policy"] = "same-origin"
        response["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response["Server"] = "fordspy"
        if request.path.startswith("/admin/"):
            response["Content-Security-Policy"] = (
                "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'"
            )
        return response


class RequestBodySizeLimitMiddleware:
    """Reject requests whose Content-Length exceeds 1 MB before body is parsed."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            if int(request.META.get("CONTENT_LENGTH") or 0) > _MAX_BODY:
                return JsonResponse(
                    {
                        "error": {
                            "code": "PAYLOAD_TOO_LARGE",
                            "message": "Request body exceeds maximum allowed size.",
                            "details": {},
                        },
                        "request_id": getattr(request, "request_id", uuid.uuid4().hex),
                    },
                    status=413,
                )
        except (ValueError, TypeError):
            pass
        return self.get_response(request)


class HmacVerificationMiddleware:
    """Optional HMAC payload signing for service-to-service calls.

    Enabled via HMAC_VERIFICATION_ENABLED=True env var.
    Signature header: X-Signature: sha256=<hex>
    Timestamp header: X-Signature-Timestamp: <unix epoch>
    Replay window: 5 minutes.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, "HMAC_VERIFICATION_ENABLED", False) and (
            "HTTP_X_SIGNATURE" in request.META
        ):
            result = self._verify(request)
            if result is not None:
                return result
        return self.get_response(request)

    def _verify(self, request):
        from apps.accounts.models import ServiceClient

        sig_header = request.META.get("HTTP_X_SIGNATURE", "")
        ts_header = request.META.get("HTTP_X_SIGNATURE_TIMESTAMP", "")

        if not sig_header.startswith("sha256="):
            return self._reject(request)

        try:
            ts = int(ts_header)
        except (ValueError, TypeError):
            return self._reject(request)

        if abs(time.time() - ts) > 300:
            return self._reject(request)

        try:
            body = request.body
        except Exception:
            return self._reject(request)

        provided_sig = sig_header[len("sha256=") :]
        for client in ServiceClient.objects.filter(is_active=True):
            secret = (
                client.hmac_secret.encode()
                if isinstance(client.hmac_secret, str)
                else client.hmac_secret
            )  # noqa: E501
            expected = hmac_lib.new(secret, body, hashlib.sha256).hexdigest()
            if hmac_lib.compare_digest(expected, provided_sig):
                return None  # valid signature

        return self._reject(request)

    def _reject(self, request):
        return JsonResponse(
            {
                "error": {
                    "code": "AUTHENTICATION_FAILED",
                    "message": "Invalid or missing HMAC signature.",
                    "details": {},
                },
                "request_id": getattr(request, "request_id", uuid.uuid4().hex),
            },
            status=401,
        )
