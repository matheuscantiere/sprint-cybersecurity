from rest_framework import serializers
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)

from .models import AuditLog


class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class RefreshSerializer(TokenRefreshSerializer):
    pass


class AuditLogSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="user.username", default=None, allow_null=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "event",
            "user",
            "username_attempt",
            "ip_address",
            "user_agent",
            "request_id",
            "timestamp",
        ]
