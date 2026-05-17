"""App configuration for Email Marketing."""

from django.apps import AppConfig


class EmailMarketingConfig(AppConfig):
    """Configuration for the Email Marketing Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.email_marketing"
    verbose_name = "Email Marketing"
