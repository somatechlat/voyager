"""Automation sequence model with trigger-based branching."""

from __future__ import annotations

from django.db import models


class AutomationSequence(models.Model):
    """A trigger-based email automation sequence with branching logic.

    Sequences are built from steps (email, delay, condition, goal)
    stored as JSON. The automation engine processes each step
    based on subscriber actions and conditions.

    Attributes:
        id: Auto-incrementing primary key.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        name: Sequence name.
        trigger_type: What triggers the sequence.
        trigger_config: JSON trigger configuration.
        steps: JSON array of sequence steps.
        status: Sequence lifecycle status.
        total_enrolled: Total subscribers enrolled.
        total_completed: Total subscribers who completed.
        total_exited: Total subscribers who exited early.
        avg_completion_time_hours: Average time to complete.
        entry_criteria: JSON enrollment criteria.
        exit_criteria: JSON early-exit criteria.
        frequency_cap: Max times a subscriber can enter.
        created_at: Timestamp when created.
        updated_at: Timestamp when last updated.
    """

    class Status(models.TextChoices):
        """Sequence lifecycle statuses."""

        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        ARCHIVED = "archived", "Archived"

    class TriggerType(models.TextChoices):
        """Available trigger types."""

        LIST_SIGNUP = "list_signup", "List Signup"
        PURCHASE = "purchase", "Purchase"
        DATE = "date", "Date"
        BEHAVIOR = "behavior", "Behavior"
        API_EVENT = "api_event", "API Event"
        TAG_ADDED = "tag_added", "Tag Added"
        EMAIL_ACTION = "email_action", "Email Action"
        SCORE_CHANGE = "score_change", "Score Change"
        ABANDONED_CART = "abandoned_cart", "Abandoned Cart"
        PAGE_VISIT = "page_visit", "Page Visit"

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    name = models.CharField(
        max_length=255,
        help_text="Sequence name",
    )
    trigger_type = models.CharField(
        max_length=20,
        choices=TriggerType.choices,
        default=TriggerType.LIST_SIGNUP,
        db_index=True,
        help_text="What triggers the sequence",
    )
    trigger_config = models.JSONField(
        default=dict,
        help_text="Trigger configuration (listId, productId, etc.)",
    )
    steps = models.JSONField(
        default=list,
        help_text="JSON array of sequence steps",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text="Sequence lifecycle status",
    )
    total_enrolled = models.PositiveIntegerField(
        default=0,
        help_text="Total subscribers enrolled",
    )
    total_completed = models.PositiveIntegerField(
        default=0,
        help_text="Total subscribers who completed",
    )
    total_exited = models.PositiveIntegerField(
        default=0,
        help_text="Total subscribers who exited early",
    )
    avg_completion_time_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Average time to complete in hours",
    )
    entry_criteria = models.JSONField(
        default=dict,
        blank=True,
        help_text="Enrollment criteria",
    )
    exit_criteria = models.JSONField(
        default=dict,
        blank=True,
        help_text="Early-exit criteria",
    )
    frequency_cap = models.PositiveIntegerField(
        default=0,
        help_text="Max times a subscriber can enter (0=unlimited)",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when last updated",
    )

    class Meta:
        db_table = "voyager_automation_sequence"
        verbose_name = "Automation Sequence"
        verbose_name_plural = "Automation Sequences"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "trigger_type"]),
            models.Index(fields=["tenant_id", "status", "trigger_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.trigger_type})"

    @property
    def completion_rate(self) -> float:
        """Calculate completion rate as percentage."""
        if self.total_enrolled > 0:
            return round((self.total_completed / self.total_enrolled) * 100.0, 2)
        return 0.0

    @property
    def step_count(self) -> int:
        """Return number of steps in the sequence."""
        return len(self.steps) if isinstance(self.steps, list) else 0
