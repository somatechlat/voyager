"""Campaign model with 8-stage lifecycle."""

from __future__ import annotations

from django.db import models

from apps.clients.models.client import Client


class Campaign(models.Model):
    """A marketing campaign with 8-stage lifecycle management.

    Attributes:
        id: Auto-incrementing primary key.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        client: The client this campaign belongs to.
        name: Campaign name.
        description: Detailed campaign description.
        objective: Campaign objective (awareness, engagement, conversion, retention).
        stage: Current lifecycle stage.
        status: Campaign status within the stage.
        start_date: Campaign start date.
        end_date: Campaign end date.
        budget: Total campaign budget.
        current_spend: Total amount spent so far.
        currency: Three-letter currency code.
        pacing_type: Budget pacing algorithm type.
        attribution_model: Revenue attribution model.
        channels: JSON list of configured channel types.
        target_audience: JSON audience targeting configuration.
        kpis: JSON key performance indicators.
        alerts_sent: JSON tracking of which budget alerts have been sent.
        parent_campaign: Optional parent campaign for hierarchies.
        cloned_from: Original campaign if this is a clone.
        created_by: User ID of the campaign creator.
        brief_approved: Whether the brief has been approved.
        all_creatives_approved: Whether all creative assets are approved.
        approval_status: Stakeholder approval status.
        all_platforms_published: Whether all platform content is live.
        created_at: Timestamp when created.
        updated_at: Timestamp when last updated.
    """

    class Stage(models.TextChoices):
        """Campaign lifecycle stages."""

        PLANNING = "planning", "Planning"
        BRIEF = "brief", "Brief"
        CREATIVE = "creative", "Creative"
        APPROVAL = "approval", "Approval"
        LAUNCH = "launch", "Launch"
        MONITORING = "monitoring", "Monitoring"
        OPTIMIZATION = "optimization", "Optimization"
        REPORTING = "reporting", "Reporting"

    class Status(models.TextChoices):
        """Campaign status values."""

        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"
        ARCHIVED = "archived", "Archived"
        CANCELLED = "cancelled", "Cancelled"

    class Objective(models.TextChoices):
        """Campaign objective types."""

        AWARENESS = "awareness", "Awareness"
        ENGAGEMENT = "engagement", "Engagement"
        CONVERSION = "conversion", "Conversion"
        RETENTION = "retention", "Retention"

    class PacingType(models.TextChoices):
        """Budget pacing algorithm types."""

        EVEN = "even", "Even"
        ACCELERATED = "accelerated", "Accelerated"
        FRONT_LOADED = "front_loaded", "Front Loaded"
        PERFORMANCE = "performance", "Performance"

    class AttributionModel(models.TextChoices):
        """Revenue attribution models."""

        FIRST_TOUCH = "first_touch", "First Touch"
        LAST_TOUCH = "last_touch", "Last Touch"
        LINEAR = "linear", "Linear"
        TIME_DECAY = "time_decay", "Time Decay"

    class ApprovalStatus(models.TextChoices):
        """Stakeholder approval statuses."""

        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CHANGES_REQUESTED = "changes_requested", "Changes Requested"

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="campaigns",
        help_text="The client this campaign belongs to",
    )
    name = models.CharField(max_length=255, help_text="Campaign name")
    description = models.TextField(blank=True, help_text="Detailed campaign description")
    objective = models.CharField(
        max_length=20,
        choices=Objective.choices,
        default=Objective.AWARENESS,
        db_index=True,
        help_text="Campaign objective type",
    )
    stage = models.CharField(
        max_length=20,
        choices=Stage.choices,
        default=Stage.PLANNING,
        db_index=True,
        help_text="Current lifecycle stage",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text="Campaign status",
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Campaign start date",
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Campaign end date",
    )
    budget = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total campaign budget",
    )
    current_spend = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text="Total amount spent so far",
    )
    currency = models.CharField(
        max_length=3,
        default="USD",
        help_text="Three-letter currency code",
    )
    pacing_type = models.CharField(
        max_length=20,
        choices=PacingType.choices,
        default=PacingType.EVEN,
        help_text="Budget pacing algorithm",
    )
    attribution_model = models.CharField(
        max_length=20,
        choices=AttributionModel.choices,
        default=AttributionModel.LAST_TOUCH,
        help_text="Revenue attribution model",
    )
    channels = models.JSONField(
        default=list,
        blank=True,
        help_text="List of configured channel types",
    )
    target_audience = models.JSONField(
        default=dict,
        blank=True,
        help_text="Audience targeting configuration",
    )
    kpis = models.JSONField(
        default=dict,
        blank=True,
        help_text="Key performance indicators configuration",
    )
    alerts_sent = models.JSONField(
        default=dict,
        blank=True,
        help_text="Tracking of budget alerts already sent",
    )
    parent_campaign = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_campaigns",
        help_text="Parent campaign for hierarchies",
    )
    cloned_from = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clones",
        help_text="Original campaign if this is a clone",
    )
    created_by = models.CharField(
        max_length=256,
        blank=True,
        db_index=True,
        help_text="User ID of the campaign creator",
    )
    brief_approved = models.BooleanField(
        default=False,
        help_text="Whether the brief has been approved",
    )
    all_creatives_approved = models.BooleanField(
        default=False,
        help_text="Whether all creative assets are approved",
    )
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        help_text="Stakeholder approval status",
    )
    all_platforms_published = models.BooleanField(
        default=False,
        help_text="Whether all platform content is live",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when last updated",
    )

    class Meta:
        db_table = "voyager_campaign"
        verbose_name = "Campaign"
        verbose_name_plural = "Campaigns"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "stage"]),
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "client", "stage"]),
            models.Index(fields=["tenant_id", "start_date", "end_date"]),
            models.Index(fields=["tenant_id", "objective"]),
            models.Index(fields=["tenant_id", "created_by"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.stage})"

    @property
    def spend_percentage(self) -> float:
        """Calculate spend as a percentage of budget.

        Returns:
            Spend percentage, or 0.0 if budget is None or zero.
        """
        if self.budget and self.budget > 0:
            return (float(self.current_spend) / float(self.budget)) * 100.0
        return 0.0

    @property
    def days_remaining(self) -> int | None:
        """Calculate days remaining until campaign end.

        Returns:
            Days remaining, or None if end_date is not set.
        """
        from datetime import date

        if self.end_date:
            return max(0, (self.end_date - date.today()).days)
        return None

    @property
    def days_elapsed(self) -> int | None:
        """Calculate days elapsed since campaign start.

        Returns:
            Days elapsed, or None if start_date is not set.
        """
        from datetime import date

        if self.start_date:
            return max(0, (date.today() - self.start_date).days)
        return None
