from django.apps import AppConfig


class SharedConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "berryllium.shared"

    def ready(self):
        from berryllium.shared import options
