"""Management command: delete AuditLog rows older than 180 days."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import AuditLog


class Command(BaseCommand):
    help = "Delete AuditLog rows older than 180 days."

    def handle(self, *args, **options) -> None:
        cutoff = timezone.now() - timedelta(days=180)
        deleted, _ = AuditLog.objects.filter(timestamp__lt=cutoff).delete()
        self.stdout.write(
            self.style.SUCCESS(f"Pruned {deleted} audit log entries older than {cutoff.date()}.")
        )
