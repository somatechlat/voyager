"""Client portal management service.

Handles portal configuration, white-label branding settings,
and custom domain management.
"""

from __future__ import annotations

import logging
from typing import Any

from ninja.errors import HttpError

from apps.clients.models.client import Client
from apps.clients.models.portal import ClientPortal

logger = logging.getLogger(__name__)


class PortalService:
    """Service for client portal lifecycle management.

    Provides CRUD operations for white-label client portals,
    branding configuration, and activation controls.
    """

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @staticmethod
    def get_or_create(client_id: int, data: dict[str, Any]) -> ClientPortal:
        """Get existing portal or create a new one for a client.

        Args:
            client_id: The client primary key.
            data: Portal configuration data.

        Returns:
            The ClientPortal instance.

        Raises:
            HttpError: 404 if the client does not exist.
        """
        try:
            client = Client.objects.get(id=client_id)
        except Client.DoesNotExist:
            raise HttpError(404, "Client not found")

        portal, created = ClientPortal.objects.get_or_create(
            client=client,
            defaults={
                "slug": data.get("slug", client.slug),
                "branding": data.get("branding", {}),
                "custom_domain": data.get("custom_domain", ""),
                "is_active": data.get("is_active", True),
            },
        )
        if created:
            logger.info("Portal created for client: %s", client.name)
        return portal

    @staticmethod
    def get_by_client(client_id: int) -> ClientPortal:
        """Retrieve the portal for a client.

        Args:
            client_id: The client primary key.

        Returns:
            The ClientPortal instance.

        Raises:
            HttpError: 404 if no portal exists for the client.
        """
        try:
            return ClientPortal.objects.get(client_id=client_id)
        except ClientPortal.DoesNotExist:
            raise HttpError(404, "Portal not found for this client")

    @staticmethod
    def update(portal: ClientPortal, data: dict[str, Any]) -> ClientPortal:
        """Update portal configuration.

        Args:
            portal: The ClientPortal instance.
            data: Dictionary of fields to update.

        Returns:
            The updated ClientPortal instance.
        """
        for key, value in data.items():
            if value is not None and hasattr(portal, key):
                setattr(portal, key, value)
        portal.save()
        logger.info("Portal updated for client: %s", portal.client.name)
        return portal

    @staticmethod
    def delete(portal: ClientPortal) -> None:
        """Delete a client portal.

        Args:
            portal: The ClientPortal instance to delete.
        """
        client_name = portal.client.name
        portal.delete()
        logger.info("Portal deleted for client: %s", client_name)

    # ------------------------------------------------------------------
    # White-label settings
    # ------------------------------------------------------------------

    @staticmethod
    def update_branding(
        portal: ClientPortal,
        branding: dict[str, Any],
    ) -> ClientPortal:
        """Update the branding configuration for a portal.

        Merges the new branding values with existing configuration.

        Args:
            portal: The ClientPortal instance.
            branding: Dictionary of branding settings:
                - logo: URL to the logo image.
                - favicon: URL to the favicon.
                - primaryColor: Primary brand color hex.
                - secondaryColor: Secondary brand color hex.
                - fontFamily: Font family name.
                - customCSS: Custom CSS string.

        Returns:
            The updated ClientPortal instance.
        """
        existing: dict[str, Any] = portal.branding or {}
        existing.update(branding)
        portal.branding = existing
        portal.save()
        logger.info("Branding updated for portal: %s", portal.slug)
        return portal

    @staticmethod
    def validate_custom_domain(portal: ClientPortal) -> dict[str, Any]:
        """Validate a custom domain configuration.

        Args:
            portal: The ClientPortal instance.

        Returns:
            Dictionary with validation results:
                - valid: Whether the domain is valid.
                - domain: The domain being validated.
                - errors: List of validation error messages.
        """
        domain = portal.custom_domain
        errors: list[str] = []

        if not domain:
            return {"valid": True, "domain": "", "errors": []}

        if " " in domain:
            errors.append("Domain cannot contain spaces")

        if "/" in domain:
            errors.append("Domain cannot contain path segments")

        if not domain.replace("-", "").replace(".", "").isalnum():
            errors.append("Domain contains invalid characters")

        if len(domain) > 253:
            errors.append("Domain exceeds maximum length")

        return {
            "valid": len(errors) == 0,
            "domain": domain,
            "errors": errors,
        }
