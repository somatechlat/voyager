"""Audience segment model with dynamic rules and RFM support."""

from __future__ import annotations

from django.db import models


class AudienceSegment(models.Model):
    """An audience segment for targeting email campaigns.

    Supports static lists, dynamic rules-based segments,
    behavioral segments, and predictive/RFM segments.

    Attributes:
        id: Auto-incrementing primary key.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        name: Segment name.
        segment_type: Type of segment (static, dynamic, behavioral, predictive).
        rules: JSON segment rules definition.
        subscriber_count: Cached subscriber count.
        last_calculated: When the count was last refreshed.
        description: Human-readable segment description.
        rfm_enabled: Whether RFM scoring is used.
        rfm_config: JSON RFM scoring configuration.
        predictive_type: Predictive model type if applicable.
        is_system: Whether this is a system segment.
        created_at: Timestamp when created.
        updated_at: Timestamp when last updated.
    """

    class Type(models.TextChoices):
        """Segment type options."""

        STATIC = "static", "Static"
        DYNAMIC = "dynamic", "Dynamic"
        BEHAVIORAL = "behavioral", "Behavioral"
        PREDICTIVE = "predictive", "Predictive"

    class PredictiveType(models.TextChoices):
        """Predictive segmentation model types."""

        CHURN_RISK = "churn_risk", "Churn Risk"
        HIGH_LTV = "high_ltv", "High LTV"
        ENGAGEMENT_PROPENSITY = "engagement_propensity", "Engagement Propensity"
        NONE = "none", "None"

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    name = models.CharField(
        max_length=255,
        help_text="Segment name",
    )
    segment_type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.STATIC,
        db_index=True,
        help_text="Segment type",
    )
    rules = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON segment rules definition",
    )
    subscriber_count = models.PositiveIntegerField(
        default=0,
        help_text="Cached subscriber count",
    )
    last_calculated = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the count was last refreshed",
    )
    description = models.TextField(
        blank=True,
        help_text="Human-readable segment description",
    )
    rfm_enabled = models.BooleanField(
        default=False,
        help_text="Whether RFM scoring is used",
    )
    rfm_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="RFM scoring configuration (recency, frequency, monetary thresholds)",
    )
    predictive_type = models.CharField(
        max_length=30,
        choices=PredictiveType.choices,
        default=PredictiveType.NONE,
        help_text="Predictive model type",
    )
    is_system = models.BooleanField(
        default=False,
        help_text="Whether this is a system segment",
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
        db_table = "voyager_audience_segment"
        verbose_name = "Audience Segment"
        verbose_name_plural = "Audience Segments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "segment_type"]),
            models.Index(fields=["tenant_id", "predictive_type"]),
            models.Index(fields=["tenant_id", "is_system"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.segment_type})"
