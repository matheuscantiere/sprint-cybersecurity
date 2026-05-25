"""Management command: anonymize users who have been inactive for 365+ days."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Anonymize users who have been inactive (is_active=False) for 365+ days."

    def handle(self, *args, **options) -> None:
        cutoff = timezone.now() - timedelta(days=365)
        users = User.objects.filter(is_active=False, date_joined__lt=cutoff).exclude(
            username__startswith="deleted_"
        )
        count = 0
        for user in users:
            user.username = f"deleted_{user.pk}"
            user.email = ""
            user.role = "VIEWER"
            user.save(update_fields=["username", "email", "role"])
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Anonymized {count} inactive user(s)."))
