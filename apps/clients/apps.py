"""App configuration for Clients."""

from django.apps import AppConfig


class ClientsConfig(AppConfig):
    """Configuration for the Clients Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.clients"
    verbose_name = "Clients"
