import secrets

from django.db import migrations


def seed_fordspy_frontend_client(apps, schema_editor):
    ServiceClient = apps.get_model("accounts", "ServiceClient")
    if not ServiceClient.objects.filter(name="fordspy-frontend").exists():
        ServiceClient.objects.create(
            name="fordspy-frontend",
            hmac_secret=secrets.token_hex(64),
        )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_serviceclient"),
    ]

    operations = [
        migrations.RunPython(
            seed_fordspy_frontend_client,
            migrations.RunPython.noop,
        ),
    ]
