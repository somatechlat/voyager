"""Context assembly model for agent decision-making."""

from __future__ import annotations

from django.db import models


class AgentContext(models.Model):
    """Snapshot of assembled context for an agent decision.

    Captures the full context payload (brand, audience, performance, memories,
    current state) that was fed to the agent at execution time for later
    analysis and learning.

    Attributes:
        id: Auto-incrementing primary key.
        agent: The agent this context was assembled for.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        task_type: The type of task being executed.
        brand_context: JSON brand guidelines snapshot.
        audience_context: JSON audience personas snapshot.
        performance_context: JSON recent performance data.
        memory_ids: List of memory entry IDs included in context.
        current_state: JSON active campaigns, scheduled content, pending approvals.
        assembled_at: When the context was assembled.
        token_estimate: Estimated token count of the assembled context.
        created_at: Creation timestamp.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    agent = models.ForeignKey(
        "ai_agents.AIAgent",
        on_delete=models.CASCADE,
        related_name="contexts",
        help_text="The agent this context was assembled for",
    )
    tenant_id = models.CharField(
        max_length=128, db_index=True, help_text="Tenant identifier for multi-tenancy isolation"
    )
    task_type = models.CharField(max_length=50, help_text="The type of task being executed")
    brand_context = models.JSONField(
        default=dict, blank=True, help_text="Brand guidelines snapshot"
    )
    audience_context = models.JSONField(
        default=dict, blank=True, help_text="Audience personas snapshot"
    )
    performance_context = models.JSONField(
        default=dict, blank=True, help_text="Recent performance data snapshot"
    )
    memory_ids = models.JSONField(
        default=list, blank=True, help_text="List of memory entry IDs included in context"
    )
    current_state = models.JSONField(
        default=dict,
        blank=True,
        help_text="Active campaigns, scheduled content, pending approvals",
    )
    assembled_at = models.DateTimeField(
        auto_now_add=True, help_text="When the context was assembled"
    )
    token_estimate = models.IntegerField(
        default=0, help_text="Estimated token count of the assembled context"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the record was created"
    )

    class Meta:
        db_table = "voyager_agent_context"
        verbose_name = "Agent Context"
        verbose_name_plural = "Agent Contexts"
        ordering = ["-assembled_at"]
        indexes = [
            models.Index(fields=["tenant_id", "agent", "-assembled_at"]),
            models.Index(fields=["agent", "task_type"]),
        ]

    def __str__(self) -> str:
        return f"Context for {self.agent.name} task={self.task_type}"
