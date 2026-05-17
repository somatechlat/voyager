"""App configuration for Strategy."""

from django.apps import AppConfig


class StrategyConfig(AppConfig):
    """Configuration for the Strategy Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.strategy"
    verbose_name = "Strategy"
