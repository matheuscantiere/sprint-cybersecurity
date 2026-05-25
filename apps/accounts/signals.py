from django.db.models.signals import pre_save


def _handle_admin_role(sender, instance, **kwargs) -> None:
    if instance.role == "ADMIN":
        instance.is_staff = True


def connect() -> None:
    from .models import User

    pre_save.connect(_handle_admin_role, sender=User)
