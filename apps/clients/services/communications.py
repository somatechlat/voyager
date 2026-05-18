"""Communication logging service.

Handles creating, updating, and querying communication log entries
for client interactions. Supports email sync hooks for auto-logging.
"""

from __future__ import annotations

import logging
from typing import Any

from django.db.models import QuerySet
from ninja.errors import HttpError

from apps.clients.models.client import Client, ClientContact
from apps.clients.models.communication import CommunicationLog
from apps.clients.models.project import Project

logger = logging.getLogger(__name__)


class CommunicationService:
    """Service for communication log management.

    Provides CRUD operations for communication logs, auto-logging
    from email data, and search capabilities across client interactions.
    """

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @staticmethod
    def create(tenant_id: str, client_id: int, data: dict[str, Any]) -> CommunicationLog:
        """Create a communication log entry.

        Args:
            tenant_id: The tenant identifier.
            client_id: The client primary key.
            data: Dictionary of communication field values.

        Returns:
            The newly created CommunicationLog instance.

        Raises:
            HttpError: 404 if the client does not exist.
        """
        try:
            client = Client.objects.get(tenant_id=tenant_id, id=client_id)
        except Client.DoesNotExist:
            raise HttpError(404, "Client not found")

        project_id = data.pop("project_id", None)
        project = None
        if project_id:
            try:
                project = Project.objects.get(tenant_id=tenant_id, id=project_id)
            except Project.DoesNotExist:
                pass

        log = CommunicationLog.objects.create(
            tenant_id=tenant_id,
            client=client,
            project=project,
            **data,
        )
        logger.info(
            "Communication logged: %s for client %s",
            log.comm_type,
            client.name,
        )
        return log

    @staticmethod
    def list_communications(
        tenant_id: str,
        client_id: int | None = None,
        comm_type: str | None = None,
        project_id: int | None = None,
    ) -> QuerySet[CommunicationLog]:
        """List communication logs with optional filtering.

        Args:
            tenant_id: The tenant identifier.
            client_id: Optional client filter.
            comm_type: Optional communication type filter.
            project_id: Optional project filter.

        Returns:
            QuerySet of matching CommunicationLog instances.
        """
        qs: QuerySet[CommunicationLog] = CommunicationLog.objects.filter(tenant_id=tenant_id)
        if client_id:
            qs = qs.filter(client_id=client_id)
        if comm_type:
            qs = qs.filter(comm_type=comm_type)
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs.order_by("-created_at")

    @staticmethod
    def get_by_id(tenant_id: str, log_id: int) -> CommunicationLog:
        """Retrieve a single communication log entry.

        Args:
            tenant_id: The tenant identifier.
            log_id: The log entry primary key.

        Returns:
            The CommunicationLog instance.

        Raises:
            HttpError: 404 if the log entry does not exist.
        """
        try:
            return CommunicationLog.objects.get(tenant_id=tenant_id, id=log_id)
        except CommunicationLog.DoesNotExist:
            raise HttpError(404, "Communication log not found")

    @staticmethod
    def update(log: CommunicationLog, data: dict[str, Any]) -> CommunicationLog:
        """Update a communication log entry.

        Args:
            log: The CommunicationLog instance to update.
            data: Dictionary of fields to update.

        Returns:
            The updated CommunicationLog instance.
        """
        for key, value in data.items():
            if value is not None and hasattr(log, key):
                setattr(log, key, value)
        log.save()
        logger.info("Communication log updated: %s", log.id)
        return log

    @staticmethod
    def delete(log: CommunicationLog) -> None:
        """Delete a communication log entry.

        Args:
            log: The CommunicationLog instance to delete.
        """
        log_id = log.id
        log.delete()
        logger.info("Communication log deleted: %s", log_id)

    # ------------------------------------------------------------------
    # Email sync hooks
    # ------------------------------------------------------------------

    @staticmethod
    def auto_log_email(
        tenant_id: str,
        email_data: dict[str, Any],
        client_id: int | None = None,
    ) -> CommunicationLog | None:
        """Auto-log an email by matching it to a client.

        Attempts to match the email to a client by provided client_id,
        or falls back to domain matching from the sender address.

        Args:
            tenant_id: The tenant identifier.
            email_data: Dictionary containing email fields:
                - from_address: Sender email address.
                - to_addresses: List of recipient addresses.
                - subject: Email subject.
                - body: Email body content.
                - cc: List of CC addresses.
                - thread_id: Optional email thread identifier.
                - attachments: List of attachment metadata.
            client_id: Explicit client ID if known.

        Returns:
            The created CommunicationLog, or None if no client match.
        """
        matched_client_id = client_id

        if not matched_client_id and email_data.get("from_address"):
            domain = email_data["from_address"].split("@")[-1].lower()
            try:
                client = Client.objects.get(
                    tenant_id=tenant_id,
                    website__icontains=domain,
                )
                matched_client_id = client.id
            except Client.DoesNotExist:
                # Try matching via contact email domain
                contact = (
                    ClientContact.objects.filter(
                        email__icontains=domain,
                        client__tenant_id=tenant_id,
                    )
                    .select_related("client")
                    .first()
                )
                if contact:
                    matched_client_id = contact.client.id

        if not matched_client_id:
            logger.info("No client match for email: %s", email_data.get("subject"))
            return None

        # Extract project reference from subject if present
        project = None
        subject = email_data.get("subject", "")
        import re

        project_tag = re.search(r"\[project:(\d+)\]", subject)
        if project_tag:
            try:
                project = Project.objects.get(
                    tenant_id=tenant_id,
                    id=int(project_tag.group(1)),
                )
            except Project.DoesNotExist:
                pass

        metadata: dict[str, Any] = {
            "from_address": email_data.get("from_address", ""),
            "to_addresses": email_data.get("to_addresses", []),
            "cc": email_data.get("cc", []),
            "thread_id": email_data.get("thread_id", ""),
            "attachments": email_data.get("attachments", []),
            "auto_logged": True,
        }

        log = CommunicationService.create(
            tenant_id=tenant_id,
            client_id=matched_client_id,
            data={
                "project": project,
                "comm_type": CommunicationLog.CommType.EMAIL,
                "direction": email_data.get("direction", "inbound"),
                "subject": subject,
                "content": email_data.get("body", ""),
                "metadata": metadata,
            },
        )
        logger.info("Auto-logged email for client %s: %s", matched_client_id, subject)
        return log
