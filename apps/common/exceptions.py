import logging
import uuid

from rest_framework import status
from rest_framework.exceptions import APIException, AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("apps.common.exceptions")


class NotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "NOT_FOUND"

    def __init__(self, message: str, resource: str | None = None, **extra_details):
        self.detail = message
        self.resource = resource
        self.extra_details = extra_details


def _get_request_id(request) -> str:
    if request is not None:
        rid = getattr(request, "request_id", None)
        if rid:
            return rid
        rid = request.META.get("HTTP_X_REQUEST_ID")
        if rid:
            return rid
    return uuid.uuid4().hex


def _error_response(
    code: str, message: str, details: dict | None, status_code: int, request
) -> Response:
    body = {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
        "request_id": _get_request_id(request),
    }
    resp = Response(body, status=status_code)
    resp["X-Request-ID"] = _get_request_id(request)
    return resp


def api_exception_handler(exc, context):
    request = context.get("request")

    if isinstance(exc, NotFoundError):
        details = {}
        if exc.resource:
            details["resource"] = exc.resource
        details.update(exc.extra_details)
        return _error_response("NOT_FOUND", str(exc.detail), details, 404, request)

    response = exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled exception [request_id=%s]", _get_request_id(request))
        return _error_response(
            "INTERNAL_ERROR",
            "An unexpected error occurred. Please contact support with the provided request ID.",
            {},
            500,
            request,
        )

    code_map = {
        400: "VALIDATION_ERROR",
        401: "AUTHENTICATION_FAILED",
        403: "PERMISSION_DENIED",
        404: "NOT_FOUND",
        429: "RATE_LIMITED",
        502: "UPSTREAM_UNAVAILABLE",
        503: "FEATURE_DISABLED",
    }

    status_code = response.status_code
    code = code_map.get(status_code, "INTERNAL_ERROR")

    data = response.data
    if isinstance(data, dict) and "detail" in data and len(data) == 1:
        message = str(data["detail"])
        details = {}
    elif isinstance(data, dict):
        message = code.replace("_", " ").title()
        details = {k: v if isinstance(v, list) else [v] for k, v in data.items() if k != "detail"}
    else:
        message = str(data) if data else code.replace("_", " ").title()
        details = {}

    if isinstance(exc, AuthenticationFailed):
        message = "Authentication credentials were not provided or are invalid."
        details = {}

    return _error_response(code, message, details, status_code, request)
