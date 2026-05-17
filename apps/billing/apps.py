"""App configuration for Billing."""

from django.apps import AppConfig


class BillingConfig(AppConfig):
    """Configuration for the Billing Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.billing"
    verbose_name = "Billing"
