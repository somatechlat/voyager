"""RecurringPost model — defines recurring content schedules.

Stores cron patterns, content pools, variation strategies, and
generates scheduled post instances based on recurrence rules.
"""

from __future__ import annotations

from django.db import models

from .base import TenantModel, TimeStampedModel, UUIDModel


class RecurringPost(UUIDModel, TimeStampedModel, TenantModel):
    """A recurring post series definition.

    Attributes:
        name: Human-readable series name.
        platform: Target platform.
        account_id: Platform connection UUID.
        publish_type: Feed, story, reel, etc.
        cron_expression: Cron expression for recurrence.
        content_pool: JSON list of content variations.
        variation_strategy: How to select content per instance.
        base_content: Fallback content template.
        context_json: Extra context for AI adaptation.
        start_date: Series start date.
        end_date: Optional series end date.
        timezone: IANA timezone.
        last_instance_at: Timestamp of last generated instance.
        instance_count: Total generated instances.
        is_active: Whether series is active.
        created_by: User UUID.
    """

    class VariationStrategy(models.TextChoices):
        ROUND_ROBIN = "round_robin", "Round Robin"
        RANDOM = "random", "Random"
        PERFORMANCE = "performance", "Performance"
        AI_ADAPT = "ai_adapt", "AI Adapt"

    # Identity
    name = models.CharField(
        max_length=512, help_text="Series name",
    )
    platform = models.CharField(
        max_length=32, help_text="Target platform",
    )
    account_id = models.UUIDField(
        db_index=True, help_text="Platform connection UUID",
    )
    publish_type = models.CharField(
        max_length=32, default="feed", help_text="Post type",
    )

    # Recurrence
    cron_expression = models.CharField(
        max_length=128, help_text="Cron expression for scheduling",
    )
    start_date = models.DateTimeField(help_text="Series start date")
    end_date = models.DateTimeField(
        null=True, blank=True, help_text="Optional series end",
    )
    timezone = models.CharField(
        max_length=100, default="UTC", help_text="IANA timezone",
    )

    # Content
    content_pool = models.JSONField(
        default=list, blank=True,
        help_text="List of content variations",
    )
    variation_strategy = models.CharField(
        max_length=32, choices=VariationStrategy.choices,
        default=VariationStrategy.ROUND_ROBIN,
    )
    base_content = models.JSONField(
        default=dict, blank=True,
        help_text="Base content template: {caption, hashtags, media_urls, link, alt_text}",
    )
    context_json = models.JSONField(
        default=dict, blank=True,
        help_text="Extra context for AI adaptation",
    )

    # Tracking
    last_instance_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Last generated instance timestamp",
    )
    last_instance_number = models.PositiveIntegerField(
        default=0, help_text="Last generated instance number",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.CharField(
        max_length=256, db_index=True, help_text="User UUID",
    )

    class Meta:
        db_table = "voyager_recurring_post"
        verbose_name = "Recurring Post"
        verbose_name_plural = "Recurring Posts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "is_active"]),
            models.Index(fields=["tenant_id", "platform", "account_id"]),
            models.Index(fields=["is_active", "start_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.cron_expression})"

    @property
    def platform_account_display(self) -> str:
        """Return platform display name."""
        return f"{self.platform} — {self.account_id}"

    def select_content_variant(self, instance_number: int) -> dict:
        """Select content variant based on strategy.

        Args:
            instance_number: The instance number being generated.

        Returns:
            Content dict with caption, hashtags, media_urls, etc.
        """
        import random

        pool = list(self.content_pool) if self.content_pool else []
        if not pool:
            return dict(self.base_content)

        strategy = self.variation_strategy
        if strategy == self.VariationStrategy.ROUND_ROBIN:
            if pool:
                return dict(pool[instance_number % len(pool)])
        elif strategy == self.VariationStrategy.RANDOM:
            return dict(random.choice(pool))
        elif strategy == self.VariationStrategy.PERFORMANCE:
            # Sort by score, pick highest unused
            scored = sorted(
                pool,
                key=lambda x: x.get("performance_score", 0),
                reverse=True,
            )
            if scored:
                return dict(scored[instance_number % len(scored)])
        elif strategy == self.VariationStrategy.AI_ADAPT:
            # AI adaptation — return base, service layer handles adaptation
            return dict(self.base_content)
        return dict(pool[0]) if pool else dict(self.base_content)
