"""Keyword and keyword cluster models.

Defines Keyword and KeywordCluster for 1B+ keyword database storage,
semantic clustering, and opportunity scoring.
"""

from __future__ import annotations

import uuid

from django.db import models


class KeywordCluster(models.Model):
    """A semantic cluster of related keywords.

    Keywords are grouped by semantic similarity using embedding-based
    clustering. Each cluster has a central theme, aggregate metrics,
    and a computed priority score.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    label = models.CharField(max_length=255, help_text="Central theme of the cluster")
    total_volume = models.PositiveIntegerField(default=0, help_text="Sum of monthly volumes")
    avg_difficulty = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.0, help_text="Average keyword difficulty"
    )
    priority_score = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0.0,
        help_text="Cluster priority = total_volume * (1 - avg_difficulty/100)",
    )
    embedding_vector = models.JSONField(
        default=list, blank=True, help_text="Cluster centroid embedding"
    )
    metadata_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "voyager_keyword_cluster"
        verbose_name = "Keyword Cluster"
        verbose_name_plural = "Keyword Clusters"
        ordering = ["-priority_score"]
        indexes = [
            models.Index(fields=["tenant_id", "-priority_score"]),
            models.Index(fields=["tenant_id", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.label} (vol={self.total_volume})"


class Keyword(models.Model):
    """A keyword with search metrics from 1B+ keyword database.

    Stores volume, difficulty, CPC, trend, position data, and
    semantic cluster membership for keyword research and rank tracking.
    """

    class TrendDirection(models.TextChoices):
        """Trend direction for keyword search volume."""

        RISING = "rising", "Rising"
        FALLING = "falling", "Falling"
        STABLE = "stable", "Stable"

    class CommercialIntent(models.TextChoices):
        """Detected commercial intent of the keyword."""

        INFORMATIONAL = "informational", "Informational"
        NAVIGATIONAL = "navigational", "Navigational"
        COMMERCIAL = "commercial", "Commercial"
        TRANSACTIONAL = "transactional", "Transactional"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    keyword = models.CharField(max_length=500, db_index=True, help_text="The keyword phrase")
    location = models.CharField(
        max_length=10, default="US", help_text="ISO 3166-1 country code"
    )
    language = models.CharField(
        max_length=10, default="en", help_text="ISO 639-1 language code"
    )

    # Search metrics
    monthly_volume = models.PositiveIntegerField(
        null=True, blank=True, help_text="Monthly search volume"
    )
    difficulty = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, help_text="Keyword difficulty 0-100"
    )
    cpc = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, help_text="Cost per click in USD"
    )
    trend_direction = models.CharField(
        max_length=20,
        choices=TrendDirection.choices,
        blank=True,
        help_text="12-month trend direction",
    )
    trend_growth = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        default=0.0,
        help_text="Trend growth rate (e.g. 0.15 = 15% growth)",
    )

    # Position tracking
    current_position = models.PositiveIntegerField(
        null=True, blank=True, help_text="Current SERP position"
    )
    previous_position = models.PositiveIntegerField(
        null=True, blank=True, help_text="Previous SERP position"
    )
    position_change = models.IntegerField(
        default=0, help_text="Positive = improved, negative = dropped"
    )
    target_url = models.URLField(
        max_length=2048, blank=True, help_text="Target URL for this keyword"
    )

    # SERP features
    serp_features_json = models.JSONField(
        default=list, blank=True, help_text="Detected SERP features"
    )

    # Clustering and scoring
    cluster = models.ForeignKey(
        KeywordCluster,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="keywords",
    )
    opportunity_score = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=0.0,
        help_text="Computed opportunity score",
    )
    commercial_intent = models.CharField(
        max_length=20,
        choices=CommercialIntent.choices,
        blank=True,
        help_text="Detected commercial intent",
    )
    embedding_vector = models.JSONField(
        default=list, blank=True, help_text="Keyword embedding vector"
    )

    # Tracking
    is_tracked = models.BooleanField(
        default=False, db_index=True, help_text="Whether rank tracking is enabled"
    )
    tracked_at = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(
        null=True, blank=True, help_text="Last third-party API sync"
    )
    metadata_json = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "voyager_keyword"
        verbose_name = "Keyword"
        verbose_name_plural = "Keywords"
        ordering = ["-opportunity_score"]
        indexes = [
            models.Index(fields=["tenant_id", "keyword", "location"]),
            models.Index(fields=["tenant_id", "current_position"]),
            models.Index(fields=["tenant_id", "is_tracked"]),
            models.Index(fields=["tenant_id", "-opportunity_score"]),
            models.Index(fields=["cluster", "-opportunity_score"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "keyword", "location", "language"],
                name="%(app_label)s_keyword_tenant_kw_loc_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.keyword} (pos={self.current_position})"

    def compute_position_change(self) -> int:
        """Calculate position change from previous to current.

        Returns:
            Positive integer if improved, negative if dropped, 0 if no data.
        """
        if self.previous_position is None or self.current_position is None:
            return 0
        return self.previous_position - self.current_position
