"""Audit app configuration."""

from django.apps import AppConfig


class AuditConfig(AppConfig):
    """Configuration for the Audit Django app.

    Provides immutable audit logging with SHA-256 hash chain integrity,
    log archiving after retention periods, and compliance-ready
    audit trail querying for the Voyager platform.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    verbose_name = "Voyager Audit"

    def ready(self) -> None:
        """Perform initialization when Django starts.

        Called once Django has loaded all apps. Used to register
        signal handlers for automatic audit log creation on
        model mutations across the platform.
        """
        import logging

        logging.getLogger(__name__).debug("Audit app initialized")
