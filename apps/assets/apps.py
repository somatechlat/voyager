"""App configuration for Assets."""

from django.apps import AppConfig


class AssetsConfig(AppConfig):
    """Configuration for the Assets Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.assets"
    verbose_name = "Assets"
