"""App configuration for SEO."""

from django.apps import AppConfig


class SEOConfig(AppConfig):
    """Configuration for the SEO Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.seo"
    verbose_name = "SEO"
