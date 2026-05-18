"""CommunicationLog model."""

from __future__ import annotations

from django.db import models

from apps.clients.models.client import Client
from apps.clients.models.project import Project


class CommunicationLog(models.Model):
    """A communication record between the agency and a client.

    Attributes:
        id: Auto-incrementing primary key.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        client: The client this communication is with.
        project: Optional linked project.
        comm_type: Type of communication (email, call, meeting, note).
        direction: Direction of the communication.
        subject: Subject line or brief title.
        content: Full body content of the communication.
        participant_ids: JSON list of participant user IDs.
        duration_minutes: Duration for calls/meetings.
        metadata: Extensible JSON metadata (attachments, thread_id, etc.).
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    class CommType(models.TextChoices):
        """Types of communication."""

        EMAIL = "email", "Email"
        CALL = "call", "Call"
        MEETING = "meeting", "Meeting"
        NOTE = "note", "Note"

    class Direction(models.TextChoices):
        """Direction of the communication."""

        INBOUND = "inbound", "Inbound"
        OUTBOUND = "outbound", "Outbound"
        INTERNAL = "internal", "Internal"

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="communications",
        help_text="The client this communication is with",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="communications",
        help_text="Optional linked project",
    )
    comm_type = models.CharField(
        max_length=20,
        choices=CommType.choices,
        db_index=True,
        help_text="Type of communication",
    )
    direction = models.CharField(
        max_length=10,
        choices=Direction.choices,
        default=Direction.OUTBOUND,
        help_text="Direction of the communication",
    )
    subject = models.CharField(
        max_length=500,
        blank=True,
        help_text="Subject line or brief title",
    )
    content = models.TextField(
        blank=True,
        help_text="Full body content of the communication",
    )
    participant_ids = models.JSONField(
        default=list,
        blank=True,
        help_text="List of participant user IDs",
    )
    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Duration in minutes (for calls/meetings)",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extensible metadata (attachments, thread_id, etc.)",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when the record was created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the record was last updated",
    )

    class Meta:
        db_table = "voyager_communication_log"
        verbose_name = "Communication Log"
        verbose_name_plural = "Communication Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "client", "-created_at"]),
            models.Index(fields=["tenant_id", "comm_type"]),
            models.Index(fields=["tenant_id", "project"]),
        ]

    def __str__(self) -> str:
        return f"[{self.comm_type}] {self.subject or 'No subject'}"
