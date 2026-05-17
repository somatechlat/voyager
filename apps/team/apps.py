"""App configuration for Team."""

from django.apps import AppConfig


class TeamConfig(AppConfig):
    """Configuration for the Team Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.team"
    verbose_name = "Team"
