"""CampaignChannel model — 8 marketing channel types."""

from __future__ import annotations

from django.db import models

from apps.campaigns.models.campaign import Campaign


class CampaignChannel(models.Model):
    """A marketing channel configured for a campaign.

    Supports 8 channel types: organic_social, paid_search, paid_social,
    email, seo, influencer, display, video.

    Attributes:
        id: Auto-incrementing primary key.
        campaign: Parent campaign.
        channel_type: Type of marketing channel.
        platform: Platform name (e.g. 'google_ads', 'meta_ads').
        config: JSON channel-specific configuration.
        daily_budget: Daily spend limit for this channel.
        total_spend: Total spend on this channel.
        status: Channel status.
        start_date: Channel-specific start date.
        end_date: Channel-specific end date.
        dependencies: JSON list of channel IDs this channel depends on.
        lead_time_days: Days needed before this channel can launch.
        created_at: Timestamp when created.
    """

    class ChannelType(models.TextChoices):
        """Marketing channel types."""

        ORGANIC_SOCIAL = "organic_social", "Organic Social"
        PAID_SEARCH = "paid_search", "Paid Search"
        PAID_SOCIAL = "paid_social", "Paid Social"
        EMAIL = "email", "Email"
        SEO = "seo", "SEO"
        INFLUENCER = "influencer", "Influencer"
        DISPLAY = "display", "Display"
        VIDEO = "video", "Video"

    class Status(models.TextChoices):
        """Channel statuses."""

        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"
        ERROR = "error", "Error"

    id = models.BigAutoField(primary_key=True, editable=False)
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="channel_configs",
        help_text="Parent campaign",
    )
    channel_type = models.CharField(
        max_length=30,
        choices=ChannelType.choices,
        db_index=True,
        help_text="Type of marketing channel",
    )
    platform = models.CharField(
        max_length=50,
        help_text="Platform name (e.g. google_ads, meta_ads)",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Channel-specific configuration",
    )
    daily_budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Daily spend limit for this channel",
    )
    total_spend = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text="Total spend on this channel",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text="Channel status",
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Channel-specific start date",
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Channel-specific end date",
    )
    dependencies = models.JSONField(
        default=list,
        blank=True,
        help_text="List of channel IDs this channel depends on",
    )
    lead_time_days = models.PositiveIntegerField(
        default=0,
        help_text="Days needed before this channel can launch",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when created",
    )

    class Meta:
        db_table = "voyager_campaign_channel"
        verbose_name = "Campaign Channel"
        verbose_name_plural = "Campaign Channels"
        ordering = ["channel_type", "-created_at"]
        indexes = [
            models.Index(fields=["campaign", "channel_type"]),
            models.Index(fields=["campaign", "status"]),
            models.Index(fields=["channel_type", "platform"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "channel_type", "platform"],
                name="campaign_channel_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.channel_type} ({self.platform}) — {self.campaign.name}"

    @property
    def roas(self) -> float:
        """Return ROAS for this channel from performance data.

        Returns:
            ROAS value, defaulting to 0.0 if not available.
        """
        return float(self.config.get("roas", 0.0))

    @property
    def conversions(self) -> int:
        """Return conversions for this channel from config.

        Returns:
            Conversion count, defaulting to 0.
        """
        return int(self.config.get("conversions", 0))
