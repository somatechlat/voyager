"""Content Strategy model — SP-003.

Stores content strategies with goal mapping, topic clusters, format mix,
channel allocation, content pillars, and gap analysis.
"""

from __future__ import annotations

from django.db import models

from .base import TenantModel, TimeStampedModel, UUIDModel


class ContentStrategy(UUIDModel, TimeStampedModel, TenantModel):
    """A data-driven content strategy with topic clusters and channel allocation.

    Attributes:
        name: Strategy name.
        goal: Primary marketing goal (e.g. 'brand_awareness').
        target_personas: Array of persona UUIDs this strategy targets.
        topic_clusters: JSON with pillar topics and cluster structures.
        format_mix: JSON with recommended format distribution per channel.
        channel_allocation: JSON with resource allocation per channel.
        content_pillars: JSON with pillar content themes and descriptions.
        gap_analysis: JSON identifying content gaps vs competitors.
    """

    class Goal(models.TextChoices):
        BRAND_AWARENESS = "brand_awareness", "Brand Awareness"
        LEAD_GENERATION = "lead_generation", "Lead Generation"
        ENGAGEMENT = "engagement", "Engagement"
        CONVERSION = "conversion", "Conversion"
        RETENTION = "retention", "Retention"

    name = models.CharField(
        max_length=255,
        help_text="Strategy name",
    )
    goal = models.CharField(
        max_length=50,
        choices=Goal.choices,
        blank=True,
        db_index=True,
        help_text="Primary marketing goal",
    )
    target_personas = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of persona UUIDs this strategy targets",
    )
    topic_clusters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Topic clusters: pillars, sub-topics, search volume, difficulty",
    )
    format_mix = models.JSONField(
        default=dict,
        blank=True,
        help_text="Recommended format distribution per channel with weights",
    )
    channel_allocation = models.JSONField(
        default=dict,
        blank=True,
        help_text="Resource allocation per channel: budget, effort, priority",
    )
    content_pillars = models.JSONField(
        default=list,
        blank=True,
        help_text="Content pillar themes with descriptions and target keywords",
    )
    gap_analysis = models.JSONField(
        default=dict,
        blank=True,
        help_text="Content gap analysis: missing topics, competitor coverage, opportunity score",
    )

    class Meta:
        db_table = "voyager_content_strategy"
        verbose_name = "Content Strategy"
        verbose_name_plural = "Content Strategies"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["tenant_id", "goal"]),
            models.Index(fields=["tenant_id", "-updated_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.goal})"
