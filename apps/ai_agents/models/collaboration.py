"""Multi-agent collaboration model with delegation and circular prevention."""

from __future__ import annotations

from django.db import models


class AgentCollaboration(models.Model):
    """Record of a collaboration session between multiple agents.

    Tracks delegation chains, collaboration patterns (pipeline, fan-out,
    fan-in, review, debate), and circular delegation prevention.

    Attributes:
        id: Auto-incrementing primary key.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        initiator_agent: The agent that started the collaboration.
        task_id: Identifier of the task being collaborated on.
        pattern: Collaboration pattern used.
        status: Current status of the collaboration.
        delegation_chain: Ordered list of agent IDs in the delegation chain.
        max_depth: Maximum allowed delegation depth (default 5).
        messages: JSON log of inter-agent messages.
        started_at: When the collaboration began.
        completed_at: When the collaboration finished.
        result_summary: JSON summary of the collaboration outcome.
        created_at: Creation timestamp.
        updated_at: Last-update timestamp.
    """

    class Pattern(models.TextChoices):
        """Five built-in collaboration patterns."""

        PIPELINE = "pipeline", "Pipeline"
        FAN_OUT = "fan_out", "Fan-out"
        FAN_IN = "fan_in", "Fan-in"
        REVIEW = "review", "Review"
        DEBATE = "debate", "Debate"

    class Status(models.TextChoices):
        """Collaboration lifecycle statuses."""

        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128, db_index=True, help_text="Tenant identifier for multi-tenancy isolation"
    )
    initiator_agent = models.ForeignKey(
        "ai_agents.AIAgent",
        on_delete=models.CASCADE,
        related_name="initiated_collaborations",
        help_text="The agent that started the collaboration",
    )
    task_id = models.CharField(
        max_length=128, help_text="Identifier of the task being collaborated on"
    )
    pattern = models.CharField(
        max_length=20,
        choices=Pattern.choices,
        help_text="Collaboration pattern used",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="Current status of the collaboration",
    )
    delegation_chain = models.JSONField(
        default=list, help_text="Ordered list of agent IDs in the delegation chain"
    )
    max_depth = models.IntegerField(default=5, help_text="Maximum allowed delegation depth")
    messages = models.JSONField(
        default=list, blank=True, help_text="JSON log of inter-agent messages"
    )
    started_at = models.DateTimeField(
        null=True, blank=True, help_text="When the collaboration began"
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, help_text="When the collaboration finished"
    )
    result_summary = models.JSONField(
        default=dict, blank=True, help_text="JSON summary of the collaboration outcome"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp when the record was last updated"
    )

    class Meta:
        db_table = "voyager_agent_collaboration"
        verbose_name = "Agent Collaboration"
        verbose_name_plural = "Agent Collaborations"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["initiator_agent", "status"]),
            models.Index(fields=["task_id"]),
        ]

    def __str__(self) -> str:
        return f"Collaboration {self.pattern} on {self.task_id}"
