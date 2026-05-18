from django.apps import AppConfig


class VoyantIngestionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.voyant_ingestion"
    verbose_name = "Voyant Data Ingestion"
