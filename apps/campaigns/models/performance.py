"""CampaignPerformance model for metrics aggregation."""

from __future__ import annotations

from django.db import models

from apps.campaigns.models.campaign import Campaign
from apps.campaigns.models.channel import CampaignChannel


class CampaignPerformance(models.Model):
    """Aggregated performance metrics for a campaign on a given date.

    Stores daily metrics JSON for flexible KPI tracking across
    different channel types and campaign objectives.

    Attributes:
        id: Auto-incrementing primary key.
        campaign: Parent campaign.
        channel: Optional channel for channel-level metrics.
        metric_date: Date of the metrics.
        impressions: Number of impressions.
        clicks: Number of clicks.
        conversions: Number of conversions.
        spend: Amount spent.
        revenue: Revenue generated.
        engagement_actions: Engagement actions count.
        metrics: JSON with additional flexible metrics.
        created_at: Timestamp when created.
        updated_at: Timestamp when last updated.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="performance_records",
        help_text="Parent campaign",
    )
    channel = models.ForeignKey(
        CampaignChannel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="performance_records",
        help_text="Channel for channel-level metrics",
    )
    metric_date = models.DateField(
        db_index=True,
        help_text="Date of the metrics",
    )
    impressions = models.PositiveBigIntegerField(
        default=0,
        help_text="Number of impressions",
    )
    clicks = models.PositiveBigIntegerField(
        default=0,
        help_text="Number of clicks",
    )
    conversions = models.PositiveBigIntegerField(
        default=0,
        help_text="Number of conversions",
    )
    spend = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text="Amount spent",
    )
    revenue = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text="Revenue generated",
    )
    engagement_actions = models.PositiveBigIntegerField(
        default=0,
        help_text="Engagement actions count",
    )
    metrics = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional flexible metrics (CTR, CPC, CPA, ROAS, etc)",
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
        db_table = "voyager_campaign_performance"
        verbose_name = "Campaign Performance"
        verbose_name_plural = "Campaign Performances"
        ordering = ["-metric_date", "campaign"]
        indexes = [
            models.Index(fields=["campaign", "-metric_date"]),
            models.Index(fields=["campaign", "channel", "-metric_date"]),
            models.Index(fields=["metric_date"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "channel", "metric_date"],
                name="campaign_perf_daily_uniq",
            ),
        ]

    def __str__(self) -> str:
        ch = self.channel.channel_type if self.channel else "all"
        return f"{self.campaign.name} — {ch} — {self.metric_date}"

    @property
    def ctr(self) -> float:
        """Click-through rate.

        Returns:
            CTR as a percentage, or 0.0 if no impressions.
        """
        if self.impressions > 0:
            return (self.clicks / self.impressions) * 100.0
        return 0.0

    @property
    def cpc(self) -> float:
        """Cost per click.

        Returns:
            CPC in currency units, or 0.0 if no clicks.
        """
        if self.clicks > 0:
            return float(self.spend) / self.clicks
        return 0.0

    @property
    def cpa(self) -> float:
        """Cost per acquisition.

        Returns:
            CPA in currency units, or 0.0 if no conversions.
        """
        if self.conversions > 0:
            return float(self.spend) / self.conversions
        return 0.0

    @property
    def roas(self) -> float:
        """Return on ad spend.

        Returns:
            ROAS as a multiplier, or 0.0 if no spend.
        """
        spend_val = float(self.spend)
        if spend_val > 0:
            return float(self.revenue) / spend_val
        return 0.0

    @property
    def conversion_rate(self) -> float:
        """Conversion rate.

        Returns:
            Conversion rate as a percentage, or 0.0 if no clicks.
        """
        if self.clicks > 0:
            return (self.conversions / self.clicks) * 100.0
        return 0.0
