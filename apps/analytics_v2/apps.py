"""App configuration for Analytics v2."""

from django.apps import AppConfig


class AnalyticsV2Config(AppConfig):
    """Configuration for the Analytics v2 Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.analytics_v2"
    verbose_name = "Analytics v2"
