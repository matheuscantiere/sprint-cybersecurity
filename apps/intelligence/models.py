from django.db import models


class InsightsUsage(models.Model):
    date = models.DateField(unique=True, db_index=True)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "intelligence_insights_usage"

    def __str__(self) -> str:
        return f"InsightsUsage({self.date})"

    @classmethod
    def increment_and_check(cls, cap: int) -> bool:
        """Atomically increment today's count. Return True if cap not exceeded."""
        from datetime import date

        from django.db import transaction

        today = date.today()
        with transaction.atomic():
            usage, _ = cls.objects.select_for_update().get_or_create(date=today)
            if usage.count >= cap:
                return False
            usage.count += 1
            usage.save(update_fields=["count"])
        return True
