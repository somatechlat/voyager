"""App configuration for Governance v2."""

from django.apps import AppConfig


class GovernanceV2Config(AppConfig):
    """Configuration for the Governance v2 Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.governance_v2"
    verbose_name = "Governance v2"
