from django.apps import AppConfig


class CommonConfig(AppConfig):
    name = "apps.common"
    label = "common"

    def ready(self):
        import apps.common.openapi  # noqa: F401 — registers JWT auth extension
