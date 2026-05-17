"""App configuration for Content Creation."""

from django.apps import AppConfig


class ContentCreationConfig(AppConfig):
    """Configuration for the Content Creation Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.content_creation"
    verbose_name = "Content Creation"
