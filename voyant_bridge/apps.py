"""Django app configuration for the Voyant integration bridge."""

from django.apps import AppConfig


class VoyantBridgeConfig(AppConfig):
    """Django AppConfig for voyant_bridge.

    Registers the bridge as a standalone Django app so it can be added to
    ``INSTALLED_APPS`` and participate in the Django lifecycle (checks,
    signal registration, etc.).
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "voyant_bridge"
    verbose_name = "Voyant Integration Bridge"
