"""Client management service.

Handles client CRUD operations, onboarding workflows, and status transitions.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from django.db.models import QuerySet
from ninja.errors import HttpError

from apps.clients.models.client import Client, ClientContact

logger = logging.getLogger(__name__)


class ClientService:
    """Service for client lifecycle management.

    Provides CRUD operations, onboarding flow management, and status
    transitions for client records within a tenant.
    """

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @staticmethod
    def create(tenant_id: str, data: dict[str, Any]) -> Client:
        """Create a new client record.

        Args:
            tenant_id: The tenant identifier.
            data: Dictionary of client field values.

        Returns:
            The newly created Client instance.

        Raises:
            HttpError: 400 if slug uniqueness is violated.
        """
        slug: str = data.get("slug", "")
        if Client.objects.filter(tenant_id=tenant_id, slug=slug).exists():
            raise HttpError(400, f"Client with slug '{slug}' already exists")

        contact_data = data.pop("primary_contact", None)
        client = Client.objects.create(tenant_id=tenant_id, **data)

        if contact_data:
            ClientContact.objects.create(
                client=client,
                name=contact_data.get("name", ""),
                email=contact_data.get("email", ""),
                phone=contact_data.get("phone", ""),
                role=contact_data.get("role", ""),
                is_primary=True,
            )

        logger.info("Client created: %s (tenant: %s)", client.name, tenant_id)
        return client

    @staticmethod
    def list_clients(
        tenant_id: str,
        status: str | None = None,
        tier: str | None = None,
        search: str | None = None,
    ) -> QuerySet[Client]:
        """List clients for a tenant with optional filtering.

        Args:
            tenant_id: The tenant identifier.
            status: Optional status filter.
            tier: Optional tier filter.
            search: Optional name search term.

        Returns:
            QuerySet of matching Client instances.
        """
        qs: QuerySet[Client] = Client.objects.filter(tenant_id=tenant_id)
        if status:
            qs = qs.filter(status=status)
        if tier:
            qs = qs.filter(tier=tier)
        if search:
            qs = qs.filter(name__icontains=search)
        return qs.order_by("-created_at")

    @staticmethod
    def get_by_id(tenant_id: str, client_id: int) -> Client:
        """Retrieve a single client by ID.

        Args:
            tenant_id: The tenant identifier.
            client_id: The client primary key.

        Returns:
            The Client instance.

        Raises:
            HttpError: 404 if the client does not exist.
        """
        try:
            return Client.objects.get(tenant_id=tenant_id, id=client_id)
        except Client.DoesNotExist:
            raise HttpError(404, "Client not found")

    @staticmethod
    def update(client: Client, data: dict[str, Any]) -> Client:
        """Update an existing client record.

        Only updates fields that are present and not None in the data dict.

        Args:
            client: The Client instance to update.
            data: Dictionary of fields to update.

        Returns:
            The updated Client instance.
        """
        for key, value in data.items():
            if value is not None and hasattr(client, key):
                setattr(client, key, value)
        client.save()
        logger.info("Client updated: %s", client.name)
        return client

    @staticmethod
    def delete(client: Client) -> None:
        """Delete a client and all related records.

        Args:
            client: The Client instance to delete.
        """
        name = client.name
        client.delete()
        logger.info("Client deleted: %s", name)

    # ------------------------------------------------------------------
    # Onboarding
    # ------------------------------------------------------------------

    @staticmethod
    def complete_onboarding(
        tenant_id: str,
        client_id: int,
        onboarding_data: dict[str, Any] | None = None,
    ) -> Client:
        """Complete the onboarding process for a client.

        Transitions the client from 'onboarding' status to 'active',
        updates settings with onboarding data, and logs the event.

        Args:
            tenant_id: The tenant identifier.
            client_id: The client primary key.
            onboarding_data: Optional onboarding form data to store.

        Returns:
            The updated Client instance.

        Raises:
            HttpError: 404 if the client does not exist.
        """
        client = ClientService.get_by_id(tenant_id, client_id)

        client.status = Client.Status.ACTIVE
        if onboarding_data:
            existing_settings: dict[str, Any] = client.settings or {}
            existing_settings["onboarding"] = onboarding_data
            existing_settings["onboarding_completed_at"] = datetime.utcnow().isoformat()
            client.settings = existing_settings
        client.save()

        logger.info(
            "Onboarding completed for client: %s (tenant: %s)",
            client.name,
            tenant_id,
        )
        return client

    @staticmethod
    def start_onboarding(tenant_id: str, data: dict[str, Any]) -> Client:
        """Start the onboarding process for a new client.

        Creates a client record with 'onboarding' status and initial settings.

        Args:
            tenant_id: The tenant identifier.
            data: Client intake form data including name, industry, etc.

        Returns:
            The newly created Client instance in onboarding status.
        """
        data["status"] = Client.Status.ONBOARDING
        if "slug" not in data or not data["slug"]:
            import re

            base = re.sub(r"[^a-z0-9-]", "-", data.get("name", "").lower())
            base = re.sub(r"-+", "-", base).strip("-")
            data["slug"] = base

        return ClientService.create(tenant_id, data)

    # ------------------------------------------------------------------
    # Status management
    # ------------------------------------------------------------------

    @staticmethod
    def transition_status(client: Client, new_status: str) -> Client:
        """Transition a client to a new status.

        Args:
            client: The Client instance.
            new_status: The target status value.

        Returns:
            The updated Client instance.

        Raises:
            HttpError: 400 if the status is invalid.
        """
        valid_statuses = {s.value for s in Client.Status}
        if new_status not in valid_statuses:
            raise HttpError(400, f"Invalid status '{new_status}'. Valid: {valid_statuses}")

        old_status = client.status
        client.status = new_status
        client.save()
        logger.info(
            "Client %s status changed: %s -> %s",
            client.name,
            old_status,
            new_status,
        )
        return client
