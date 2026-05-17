"""App configuration for Web Scraping v2."""

from django.apps import AppConfig


class WebScrapingV2Config(AppConfig):
    """Configuration for the Web Scraping v2 Django app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.web_scraping_v2"
    verbose_name = "Web Scraping v2"
