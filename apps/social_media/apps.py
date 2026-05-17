"""App configuration for Social Media."""

from django.apps import AppConfig


class SocialMediaConfig(AppConfig):
    """Configuration for the Social Media Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.social_media"
    verbose_name = "Social Media"
