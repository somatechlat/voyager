"""Email analytics model for per-campaign event tracking."""

from __future__ import annotations

from django.db import models

from apps.email_marketing.models.campaign import EmailCampaign


class EmailAnalytics(models.Model):
    """Aggregated email analytics for a campaign.

    Stores per-campaign metrics including opens, clicks,
    device breakdown, geographic data, and click heatmaps.

    Attributes:
        id: Auto-incrementing primary key.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        campaign: The campaign these analytics belong to.
        sent: Total emails sent.
        delivered: Total emails delivered.
        opens: Total opens.
        unique_opens: Unique opens.
        clicks: Total clicks.
        unique_clicks: Unique clicks.
        bounces: Total bounces.
        hard_bounces: Hard bounces.
        soft_bounces: Soft bounces.
        spam_complaints: Spam complaints.
        unsubscribes: Unsubscribes.
        revenue: Revenue attributed.
        conversions: Number of conversions.
        click_heatmap: JSON click heatmap data per block.
        device_breakdown: JSON device/platform stats.
        geographic_breakdown: JSON geographic stats.
        hourly_opens: JSON opens per hour.
        hourly_clicks: JSON clicks per hour.
        time_to_first_open_seconds: Average time to first open.
        time_to_first_click_seconds: Average time to first click.
        forward_count: Number of forwards.
        print_count: Number of prints.
        engagement_tiers: JSON engagement distribution.
        calculated_at: When analytics were last calculated.
        created_at: Timestamp when created.
        updated_at: Timestamp when last updated.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    campaign = models.OneToOneField(
        EmailCampaign,
        on_delete=models.CASCADE,
        related_name="analytics",
        help_text="The campaign these analytics belong to",
    )
    sent = models.PositiveIntegerField(
        default=0,
        help_text="Total emails sent",
    )
    delivered = models.PositiveIntegerField(
        default=0,
        help_text="Total emails delivered",
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
        help_text="Hard bounces",
    )
    soft_bounces = models.PositiveIntegerField(
        default=0,
        help_text="Soft bounces",
    )
    spam_complaints = models.PositiveIntegerField(
        default=0,
        help_text="Spam complaints",
    )
    unsubscribes = models.PositiveIntegerField(
        default=0,
        help_text="Unsubscribes",
    )
    revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        help_text="Revenue attributed",
    )
    conversions = models.PositiveIntegerField(
        default=0,
        help_text="Number of conversions",
    )
    click_heatmap = models.JSONField(
        default=dict,
        blank=True,
        help_text="Click heatmap data per block",
    )
    device_breakdown = models.JSONField(
        default=dict,
        blank=True,
        help_text="Device and platform statistics",
    )
    geographic_breakdown = models.JSONField(
        default=dict,
        blank=True,
        help_text="Geographic statistics",
    )
    hourly_opens = models.JSONField(
        default=dict,
        blank=True,
        help_text="Opens per hour",
    )
    hourly_clicks = models.JSONField(
        default=dict,
        blank=True,
        help_text="Clicks per hour",
    )
    time_to_first_open_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Average time to first open in seconds",
    )
    time_to_first_click_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Average time to first click in seconds",
    )
    forward_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of forwards",
    )
    print_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of prints",
    )
    engagement_tiers = models.JSONField(
        default=dict,
        blank=True,
        help_text="Engagement distribution (top 10%, 25%, etc.)",
    )
    calculated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When analytics were last calculated",
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
        db_table = "voyager_email_analytics"
        verbose_name = "Email Analytics"
        verbose_name_plural = "Email Analytics"
        ordering = ["-calculated_at", "-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "campaign"]),
            models.Index(fields=["tenant_id", "calculated_at"]),
        ]

    def __str__(self) -> str:
        return f"Analytics for {self.campaign.name}"

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
        if self.sent > 0:
            return round((self.bounces / self.sent) * 100.0, 2)
        return 0.0

    @property
    def conversion_rate(self) -> float:
        """Calculate conversion rate as percentage of delivered."""
        if self.delivered > 0:
            return round((self.conversions / self.delivered) * 100.0, 2)
        return 0.0

    @property
    def revenue_per_email(self) -> float:
        """Calculate revenue per email delivered."""
        if self.delivered > 0:
            return round(float(self.revenue) / self.delivered, 4)
        return 0.0

    @property
    def roi(self) -> float:
        """Calculate return on investment (requires cost data)."""
        return float(self.revenue)
