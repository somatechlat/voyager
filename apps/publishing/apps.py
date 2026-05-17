"""App configuration for Publishing."""

from django.apps import AppConfig


class PublishingConfig(AppConfig):
    """Configuration for the Publishing Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.publishing"
    verbose_name = "Publishing"
