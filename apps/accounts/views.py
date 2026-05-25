import uuid

from django.conf import settings
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.common.serializers import ErrorEnvelopeSerializer

from .models import AuditLog
from .serializers import LoginSerializer, LogoutSerializer
from .throttles import LoginRateThrottle


def _get_client_ip(request) -> str | None:
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _get_request_id(request) -> str:
    return getattr(request, "request_id", str(uuid.uuid4())[:8])


def _expires_in() -> int:
    return int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())


class _LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    expires_in = serializers.IntegerField()


class _RefreshResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    expires_in = serializers.IntegerField()


@extend_schema(
    tags=["Auth"],
    summary="Obtain JWT tokens",
    description="Authenticate with username and password. Returns access + refresh tokens.",
    request=LoginSerializer,
    responses={
        200: _LoginResponseSerializer,
        401: ErrorEnvelopeSerializer,
        429: ErrorEnvelopeSerializer,
    },
    examples=[
        OpenApiExample(
            "Login request",
            value={"username": "analyst", "password": "secure-password"},
            request_only=True,
        ),
        OpenApiExample(
            "Login success",
            value={"access": "<jwt-access-token>", "refresh": "<jwt-refresh-token>", "expires_in": 900},
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "Wrong credentials",
            value={
                "error": {
                    "code": "AUTHENTICATION_FAILED",
                    "message": "Authentication credentials were not provided or are invalid.",
                    "details": {},
                },
                "request_id": "abc123",
            },  # noqa: E501
            response_only=True,
            status_codes=["401"],
        ),
    ],
)
class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        username = request.data.get("username", "").lower()
        ip = _get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")[:500]
        rid = _get_request_id(request)

        try:
            response = super().post(request, *args, **kwargs)
        except Exception:
            AuditLog.objects.create(
                event=AuditLog.Event.LOGIN_FAIL,
                username_attempt=username,
                ip_address=ip,
                user_agent=ua,
                request_id=rid,
            )
            raise

        from django.contrib.auth import get_user_model

        user = get_user_model().objects.filter(username__iexact=username).first()
        AuditLog.objects.create(
            event=AuditLog.Event.LOGIN_OK,
            user=user,
            ip_address=ip,
            user_agent=ua,
            request_id=rid,
        )

        data = dict(response.data)
        data["expires_in"] = _expires_in()
        response.data = data
        return response


@extend_schema(
    tags=["Auth"],
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new access token. The old refresh token is blacklisted (rotation enabled).",  # noqa: E501
    responses={
        200: _RefreshResponseSerializer,
        401: ErrorEnvelopeSerializer,
        429: ErrorEnvelopeSerializer,
    },
    examples=[
        OpenApiExample(
            "Refresh request",
            value={"refresh": "<jwt-refresh-token>"},
            request_only=True,
        ),
        OpenApiExample(
            "Refresh success",
            value={"access": "<jwt-access-token>", "expires_in": 900},
            response_only=True,
            status_codes=["200"],
        ),
    ],
)
class RefreshView(TokenRefreshView):
    throttle_scope = "auth"

    def post(self, request, *args, **kwargs):
        ip = _get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")[:500]
        rid = _get_request_id(request)

        try:
            response = super().post(request, *args, **kwargs)
        except Exception:
            AuditLog.objects.create(
                event=AuditLog.Event.REFRESH_FAIL,
                ip_address=ip,
                user_agent=ua,
                request_id=rid,
            )
            raise

        AuditLog.objects.create(
            event=AuditLog.Event.REFRESH_OK,
            ip_address=ip,
            user_agent=ua,
            request_id=rid,
        )

        data = dict(response.data)
        data["expires_in"] = _expires_in()
        response.data = data
        return response


@extend_schema(
    tags=["Auth"],
    summary="Logout — blacklist refresh token",
    description="Blacklists the provided refresh token, preventing further use.",
    request=LogoutSerializer,
    responses={
        204: None,
        400: ErrorEnvelopeSerializer,
        401: ErrorEnvelopeSerializer,
    },
    examples=[
        OpenApiExample(
            "Logout request",
            value={"refresh": "<jwt-refresh-token>"},
            request_only=True,
        ),
    ],
)
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "auth"

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data["refresh"]
        ip = _get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")[:500]
        rid = _get_request_id(request)

        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError as exc:
            raise ValidationError({"refresh": "Invalid or already-blacklisted token."}) from exc

        AuditLog.objects.create(
            event=AuditLog.Event.LOGOUT,
            user=request.user,
            ip_address=ip,
            user_agent=ua,
            request_id=rid,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
