import uuid

from django.db import OperationalError, connection
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


@extend_schema(exclude=True)
@api_view(["GET"])
@permission_classes([AllowAny])
def health_view(request):
    try:
        connection.ensure_connection()
        db = "ok"
    except OperationalError:
        db = "error"
    status_code = 200 if db == "ok" else 503
    return Response(
        {
            "status": "ok" if db == "ok" else "degraded",
            "database": db,
            "version": "0.1.0",
        },
        status=status_code,
    )


@extend_schema(exclude=True)
class ForceErrorView(APIView):
    """Test-only view: raises RuntimeError to exercise the 500 exception handler.

    Only registered in DEBUG mode (see config/urls.py).
    """

    permission_classes = [AllowAny]

    def get(self, request):
        raise RuntimeError("intentional test error — do not use in production")


def custom_404_view(request, exception=None):
    rid = getattr(request, "request_id", uuid.uuid4().hex)
    return JsonResponse(
        {
            "error": {
                "code": "NOT_FOUND",
                "message": "The requested resource was not found.",
                "details": {},
            },
            "request_id": rid,
        },
        status=404,
    )
