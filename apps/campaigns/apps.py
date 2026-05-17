"""App configuration for Campaigns."""

from django.apps import AppConfig


class CampaignsConfig(AppConfig):
    """Configuration for the Campaigns Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.campaigns"
    verbose_name = "Campaigns"
