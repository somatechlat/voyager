"""App configuration for Workflows v2."""

from django.apps import AppConfig


class WorkflowsV2Config(AppConfig):
    """Configuration for the Workflows v2 Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workflows_v2"
    verbose_name = "Workflows v2"
