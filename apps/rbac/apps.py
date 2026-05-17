"""RBAC app configuration."""

from django.apps import AppConfig


class RbacConfig(AppConfig):
    """Configuration for the RBAC Django app.

    Provides role-based access control with role definitions,
    permission assignments, workspace isolation, and tenant-scoped
    authorization for the Voyager platform.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.rbac"
    verbose_name = "Voyager RBAC"

    def ready(self) -> None:
        """Perform initialization when Django starts.

        Called once Django has loaded all apps. Used to register
        signal handlers for automatic permission cache invalidation
        and role change propagation.
        """
        pass
