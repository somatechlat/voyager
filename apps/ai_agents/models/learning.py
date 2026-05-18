"""Agent learning loop model for outcome analysis and strategy adjustment."""

from __future__ import annotations

from django.db import models


class AgentLearningLoop(models.Model):
    """Record of an agent's learning iteration.

    Captures performance data from recent tasks, identified success and
    failure patterns, prompt adjustments, and A/B test configurations.

    Attributes:
        id: Auto-incrementing primary key.
        agent: The agent whose strategy was updated.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        analysis_period_days: Number of days of history analyzed.
        tasks_analyzed: Number of tasks included in the analysis.
        success_patterns: JSON list of patterns from successful tasks.
        failure_patterns: JSON list of patterns from failed tasks.
        prompt_adjustments: JSON diff of system prompt changes.
        ab_test_enabled: Whether A/B testing is active.
        ab_test_config: JSON A/B test configuration.
        strategy_score: Overall strategy effectiveness score (0.0 to 1.0).
        applied_at: When the strategy update was applied.
        created_at: Creation timestamp.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    agent = models.ForeignKey(
        "ai_agents.AIAgent",
        on_delete=models.CASCADE,
        related_name="learning_loops",
        help_text="The agent whose strategy was updated",
    )
    tenant_id = models.CharField(
        max_length=128, db_index=True, help_text="Tenant identifier for multi-tenancy isolation"
    )
    analysis_period_days = models.IntegerField(
        default=30, help_text="Number of days of history analyzed"
    )
    tasks_analyzed = models.IntegerField(
        default=0, help_text="Number of tasks included in the analysis"
    )
    success_patterns = models.JSONField(
        default=list, blank=True, help_text="Patterns extracted from successful tasks"
    )
    failure_patterns = models.JSONField(
        default=list, blank=True, help_text="Patterns extracted from failed tasks"
    )
    prompt_adjustments = models.JSONField(
        default=dict, blank=True, help_text="System prompt changes applied"
    )
    ab_test_enabled = models.BooleanField(
        default=False, help_text="Whether A/B testing is active"
    )
    ab_test_config = models.JSONField(
        default=dict, blank=True, help_text="A/B test configuration"
    )
    strategy_score = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        default=0.500,
        help_text="Overall strategy effectiveness score (0.0 to 1.0)",
    )
    applied_at = models.DateTimeField(
        auto_now_add=True, help_text="When the strategy update was applied"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the record was created"
    )

    class Meta:
        db_table = "voyager_agent_learning_loop"
        verbose_name = "Agent Learning Loop"
        verbose_name_plural = "Agent Learning Loops"
        ordering = ["-applied_at"]
        indexes = [
            models.Index(fields=["tenant_id", "agent", "-applied_at"]),
            models.Index(fields=["agent", "strategy_score"]),
        ]

    def __str__(self) -> str:
        return f"Learning loop for {self.agent.name} score={self.strategy_score}"
