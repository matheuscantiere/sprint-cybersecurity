from django.urls import path

from .views import AuditLogListView, LoginView, LogoutView, RefreshView

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("audit-logs/", AuditLogListView.as_view(), name="auth-audit-logs"),
]
