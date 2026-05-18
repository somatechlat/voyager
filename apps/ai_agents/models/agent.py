"""Core agent model and resource limit tracking."""

from __future__ import annotations

from django.db import models


class AIAgent(models.Model):
    """Autonomous AI agent with a specific role, capabilities, and resource budget.

    Agents operate within tenant isolation, maintain persistent memory via
    Qdrant, and expose their capabilities through the MCP tool registry.

    Attributes:
        id: Auto-incrementing primary key.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        name: Human-readable agent name.
        agent_type: One of five built-in agent roles.
        status: Current lifecycle status.
        config: JSON agent configuration (model, temperature, system prompt, tools).
        resources: JSON resource budget and current usage counters.
        schedule: Optional cron expression for scheduled runs.
        last_run_at: Timestamp of the most recent execution.
        created_at: Creation timestamp.
        updated_at: Last-update timestamp.
    """

    class AgentType(models.TextChoices):
        """Five built-in agent roles with distinct capabilities."""

        CREATIVE = "creative", "Creative"
        ANALYST = "analyst", "Analyst"
        OPTIMIZER = "optimizer", "Optimizer"
        RESEARCHER = "researcher", "Researcher"
        COORDINATOR = "coordinator", "Coordinator"

    class Status(models.TextChoices):
        """Agent lifecycle statuses."""

        IDLE = "idle", "Idle"
        RUNNING = "running", "Running"
        PAUSED = "paused", "Paused"
        SUSPENDED = "suspended", "Suspended"
        ERROR = "error", "Error"

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128, db_index=True, help_text="Tenant identifier for multi-tenancy isolation"
    )
    name = models.CharField(max_length=255, help_text="Human-readable agent name")
    agent_type = models.CharField(
        max_length=20,
        choices=AgentType.choices,
        help_text="Agent role determining default capabilities and resource budgets",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IDLE,
        help_text="Current lifecycle status",
    )
    config = models.JSONField(
        default=dict,
        help_text="Agent configuration: model, temperature, max_tokens, system_prompt, tools, memory_enabled",
    )
    resources = models.JSONField(
        default=dict,
        help_text="Resource budget and usage: max_api_calls, max_memory_mb, max_cost_per_day, used counters",
    )
    schedule = models.CharField(
        max_length=100, blank=True, help_text="Optional cron expression for scheduled runs"
    )
    last_run_at = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp of the most recent execution"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="Timestamp when the agent was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp when the agent was last updated"
    )

    class Meta:
        db_table = "voyager_ai_agent"
        verbose_name = "AI Agent"
        verbose_name_plural = "AI Agents"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "agent_type"]),
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["agent_type", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.agent_type})"


class AgentResourceLimit(models.Model):
    """Hard and soft resource limits for an agent with throttling state.

    Tracks per-resource utilization and the current throttle level applied
    when usage crosses warning thresholds.

    Attributes:
        id: Auto-incrementing primary key.
        agent: The agent these limits apply to.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        max_api_calls: Daily API call budget.
        used_api_calls: API calls consumed today.
        max_memory_mb: Memory budget in megabytes.
        used_memory_mb: Memory consumed in megabytes.
        max_cost_per_day: Daily cost budget in dollars.
        used_cost_today: Cost consumed today in dollars.
        throttle_factor: Current speed multiplier (1.0 = full speed).
        last_reset_at: When daily counters were last zeroed.
        created_at: Creation timestamp.
        updated_at: Last-update timestamp.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    agent = models.OneToOneField(
        AIAgent,
        on_delete=models.CASCADE,
        related_name="resource_limit",
        help_text="The agent these limits apply to",
    )
    tenant_id = models.CharField(
        max_length=128, db_index=True, help_text="Tenant identifier for multi-tenancy isolation"
    )
    max_api_calls = models.IntegerField(
        default=100, help_text="Daily API call budget"
    )
    used_api_calls = models.IntegerField(
        default=0, help_text="API calls consumed today"
    )
    max_memory_mb = models.IntegerField(
        default=512, help_text="Memory budget in megabytes"
    )
    used_memory_mb = models.IntegerField(
        default=0, help_text="Memory consumed in megabytes"
    )
    max_cost_per_day = models.DecimalField(
        max_digits=8, decimal_places=4, default=5.0000, help_text="Daily cost budget in dollars"
    )
    used_cost_today = models.DecimalField(
        max_digits=8, decimal_places=4, default=0.0000, help_text="Cost consumed today in dollars"
    )
    throttle_factor = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=1.00,
        help_text="Current speed multiplier (1.0 = full speed, 0.25 = severely throttled)",
    )
    last_reset_at = models.DateTimeField(
        auto_now_add=True, help_text="When daily counters were last zeroed"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp when the record was last updated"
    )

    class Meta:
        db_table = "voyager_agent_resource_limit"
        verbose_name = "Agent Resource Limit"
        verbose_name_plural = "Agent Resource Limits"
        indexes = [
            models.Index(fields=["tenant_id", "agent"]),
        ]

    def __str__(self) -> str:
        return f"Limits for {self.agent.name}"
