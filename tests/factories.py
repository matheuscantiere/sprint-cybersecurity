from factory import Sequence, post_generation
from factory.django import DjangoModelFactory

from apps.accounts.models import User


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    username = Sequence(lambda n: f"user_{n}")
    email = Sequence(lambda n: f"user_{n}@example.com")
    role = "VIEWER"

    @post_generation
    def password(obj, create, extracted, **kwargs):
        raw = extracted if extracted is not None else "Sup3rStrongPass!!!2024"
        obj.set_password(raw)
        if create:
            obj.save()
