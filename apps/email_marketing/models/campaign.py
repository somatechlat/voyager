"""Email campaign model for send management."""

from __future__ import annotations

from django.db import models

from apps.email_marketing.models.template import EmailTemplate


class EmailCampaign(models.Model):
    """An email campaign with full send tracking and analytics.

    Attributes:
        id: Auto-incrementing primary key.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        name: Campaign name.
        subject_line: Email subject line.
        preview_text: Preview text shown in inbox.
        from_name: Display name for the sender.
        from_email: Sender email address.
        reply_to: Reply-to email address.
        template: Linked email template.
        segment: Target audience segment (optional free-form ref).
        segment_id_ref: Foreign key to AudienceSegment.
        status: Campaign lifecycle status.
        scheduled_at: When the campaign should be sent.
        sent_at: When the campaign was actually sent.
        total_recipients: Number of recipients targeted.
        delivered: Number of emails delivered.
        opens: Total opens.
        unique_opens: Unique opens.
        clicks: Total clicks.
        unique_clicks: Unique clicks.
        bounces: Total bounces.
        hard_bounces: Number of hard bounces.
        spam_complaints: Number of spam complaints.
        unsubscribes: Number of unsubscribes.
        revenue: Revenue attributed to the campaign.
        send_progress_pct: Send progress percentage.
        created_at: Timestamp when created.
        updated_at: Timestamp when last updated.
    """

    class Status(models.TextChoices):
        """Campaign lifecycle statuses."""

        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        SENDING = "sending", "Sending"
        SENT = "sent", "Sent"
        PAUSED = "paused", "Paused"
        ARCHIVED = "archived", "Archived"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    name = models.CharField(
        max_length=255,
        help_text="Campaign name",
    )
    subject_line = models.CharField(
        max_length=200,
        blank=True,
        help_text="Email subject line",
    )
    preview_text = models.CharField(
        max_length=150,
        blank=True,
        help_text="Preview text shown in inbox",
    )
    from_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Display name for the sender",
    )
    from_email = models.EmailField(
        max_length=255,
        blank=True,
        help_text="Sender email address",
    )
    reply_to = models.EmailField(
        max_length=255,
        blank=True,
        help_text="Reply-to email address",
    )
    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaigns",
        help_text="Linked email template",
    )
    segment_id_ref = models.CharField(
        max_length=128,
        blank=True,
        help_text="Foreign key reference to audience segment",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text="Campaign lifecycle status",
    )
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the campaign should be sent",
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the campaign was actually sent",
    )
    total_recipients = models.PositiveIntegerField(
        default=0,
        help_text="Number of recipients targeted",
    )
    delivered = models.PositiveIntegerField(
        default=0,
        help_text="Number of emails delivered",
    )
    opens = models.PositiveIntegerField(
        default=0,
        help_text="Total opens",
    )
    unique_opens = models.PositiveIntegerField(
        default=0,
        help_text="Unique opens",
    )
    clicks = models.PositiveIntegerField(
        default=0,
        help_text="Total clicks",
    )
    unique_clicks = models.PositiveIntegerField(
        default=0,
        help_text="Unique clicks",
    )
    bounces = models.PositiveIntegerField(
        default=0,
        help_text="Total bounces",
    )
    hard_bounces = models.PositiveIntegerField(
        default=0,
        help_text="Number of hard bounces",
    )
    spam_complaints = models.PositiveIntegerField(
        default=0,
        help_text="Number of spam complaints",
    )
    unsubscribes = models.PositiveIntegerField(
        default=0,
        help_text="Number of unsubscribes",
    )
    revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        help_text="Revenue attributed to the campaign",
    )
    send_progress_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Send progress percentage",
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
        db_table = "voyager_email_campaign"
        verbose_name = "Email Campaign"
        verbose_name_plural = "Email Campaigns"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "scheduled_at"]),
            models.Index(fields=["tenant_id", "status", "scheduled_at"]),
            models.Index(fields=["tenant_id", "sent_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"

    @property
    def open_rate(self) -> float:
        """Calculate open rate as percentage."""
        if self.delivered > 0:
            return round((self.unique_opens / self.delivered) * 100.0, 2)
        return 0.0

    @property
    def click_rate(self) -> float:
        """Calculate click rate as percentage of delivered."""
        if self.delivered > 0:
            return round((self.unique_clicks / self.delivered) * 100.0, 2)
        return 0.0

    @property
    def ctr(self) -> float:
        """Calculate click-through rate as percentage of opens."""
        if self.unique_opens > 0:
            return round((self.unique_clicks / self.unique_opens) * 100.0, 2)
        return 0.0

    @property
    def bounce_rate(self) -> float:
        """Calculate bounce rate as percentage."""
        if self.total_recipients > 0:
            return round((self.bounces / self.total_recipients) * 100.0, 2)
        return 0.0

    @property
    def unsubscribe_rate(self) -> float:
        """Calculate unsubscribe rate as percentage of delivered."""
        if self.delivered > 0:
            return round((self.unsubscribes / self.delivered) * 100.0, 4)
        return 0.0

    @property
    def complaint_rate(self) -> float:
        """Calculate spam complaint rate as percentage of delivered."""
        if self.delivered > 0:
            return round((self.spam_complaints / self.delivered) * 100.0, 4)
        return 0.0

    @property
    def delivery_rate(self) -> float:
        """Calculate delivery rate as percentage."""
        if self.total_recipients > 0:
            return round((self.delivered / self.total_recipients) * 100.0, 2)
        return 0.0
