from rest_framework import serializers
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)


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
