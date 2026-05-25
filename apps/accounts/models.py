from django.contrib.auth.models import AbstractUser
from django.db import models
from django_cryptography.fields import encrypt


class Role(models.TextChoices):
    ADMIN = "ADMIN", "Administrator"
    ANALYST = "ANALYST", "Competitive Intelligence Analyst"
    VIEWER = "VIEWER", "Read-only viewer"


class User(AbstractUser):
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.VIEWER)

    class Meta:
        db_table = "accounts_user"


class AuditLog(models.Model):
    class Event(models.TextChoices):
        LOGIN_OK = "LOGIN_OK", "Login successful"
        LOGIN_FAIL = "LOGIN_FAIL", "Login failed"
        LOGOUT = "LOGOUT", "Logout"
        REFRESH_OK = "REFRESH_OK", "Token refresh successful"
        REFRESH_FAIL = "REFRESH_FAIL", "Token refresh failed"

    event = models.CharField(max_length=20, choices=Event.choices)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    username_attempt = models.CharField(max_length=150, null=True, blank=True)  # noqa: DJ001
    ip_address = encrypt(models.GenericIPAddressField(null=True, blank=True))
    user_agent = encrypt(models.CharField(max_length=500, null=True, blank=True))  # noqa: DJ001
    request_id = models.CharField(max_length=40, null=True, blank=True)  # noqa: DJ001
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["user", "timestamp"]),
        ]

    def __str__(self) -> str:
        return f"{self.event} / {self.username_attempt or self.user_id}"


class ServiceClient(models.Model):
    """Service-to-service client using HMAC payload signing."""

    name = models.CharField(max_length=100, unique=True)
    hmac_secret = encrypt(models.CharField(max_length=500))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_service_client"

    def __str__(self):
        return self.name
