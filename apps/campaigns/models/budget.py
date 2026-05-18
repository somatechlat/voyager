"""CampaignBudget model for budget history and tracking."""

from __future__ import annotations

from django.db import models

from apps.campaigns.models.campaign import Campaign


class CampaignBudget(models.Model):
    """A budget history entry for a campaign.

    Tracks allocations, spend, and adjustments over time
    with channel-level granularity.

    Attributes:
        id: Auto-incrementing primary key.
        campaign: Parent campaign.
        amount: Transaction amount (positive for allocation, negative for spend).
        type: Type of budget entry.
        channel: Optional channel reference.
        description: Human-readable description.
        metadata: JSON with additional context (roas, cpa, etc).
        created_at: Timestamp when created.
    """

    class EntryType(models.TextChoices):
        """Types of budget entries."""

        ALLOCATION = "allocation", "Allocation"
        SPEND = "spend", "Spend"
        ADJUSTMENT = "adjustment", "Adjustment"
        REFUND = "refund", "Refund"

    id = models.BigAutoField(primary_key=True, editable=False)
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="budget_entries",
        help_text="Parent campaign",
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Transaction amount (positive allocation, negative spend)",
    )
    type = models.CharField(
        max_length=20,
        choices=EntryType.choices,
        db_index=True,
        help_text="Type of budget entry",
    )
    channel = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        help_text="Channel reference (e.g. 'google_ads')",
    )
    description = models.TextField(
        blank=True,
        help_text="Human-readable description",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context (roas, cpa, impressions, etc)",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when created",
    )

    class Meta:
        db_table = "voyager_campaign_budget"
        verbose_name = "Campaign Budget Entry"
        verbose_name_plural = "Campaign Budget Entries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["campaign", "type", "-created_at"]),
            models.Index(fields=["campaign", "channel", "-created_at"]),
            models.Index(fields=["campaign", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.type} {self.amount} — {self.campaign.name}"

    @property
    def is_allocation(self) -> bool:
        """Whether this entry is a budget allocation.

        Returns:
            True if this is an allocation entry.
        """
        return self.type == self.EntryType.ALLOCATION

    @property
    def is_spend(self) -> bool:
        """Whether this entry is a spend record.

        Returns:
            True if this is a spend entry.
        """
        return self.type == self.EntryType.SPEND
