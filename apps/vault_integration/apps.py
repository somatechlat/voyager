"""
Django AppConfig for Vault Integration.

Signals the Vault system check on application ready and ensures
connectivity to HashiCorp Vault before the first request.
"""

from __future__ import annotations

import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class VaultIntegrationConfig(AppConfig):
    """Django AppConfig for the vault_integration application.

    Attributes:
        name: Full Python path to the application.
        label: Short label for the app (used in INSTALLED_APPS references).
        verbose_name: Human-readable name.
        default_auto_field: Default primary key field type.
    """

    name: str = "apps.vault_integration"
    label: str = "vault_integration"
    verbose_name: str = "Vault Integration"
    default_auto_field: str = "django.db.models.BigAutoField"

    def ready(self) -> None:
        """Called when Django registry is fully populated.

        Performs a non-blocking Vault connectivity check and logs the result.
        Does not raise — Vault being temporarily unavailable should not prevent
        Django from starting (settings may be loaded from environment as fallback).
        """
        super().ready()

        # Defer import to avoid AppRegistryNotReady
        try:
            from apps.vault_integration.client import vault_client

            if vault_client.is_authenticated():
                logger.info(
                    "Vault integration ready: connected to %s",
                    vault_client.client.url,
                )
            else:
                logger.warning(
                    "Vault integration: authentication failed on startup. "
                    "Check VOYAGER_SECRETS_VAULT_URL and VOYAGER_SECRETS_VAULT_TOKEN."
                )
        except Exception as exc:
            logger.warning(
                "Vault integration: startup check failed (%s). "
                "Application will use environment variables for settings.",
                exc,
            )
