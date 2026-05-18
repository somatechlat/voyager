"""SERP tracking models.

Defines SERPTracking and RankHistory for position monitoring,
SERP feature detection, and ranking change alerts.
"""

from __future__ import annotations

import uuid

from django.db import models


class SERPTracking(models.Model):
    """A tracked keyword for SERP position monitoring.

    Links to a Keyword record and stores tracking configuration
    including locations, devices, and alert thresholds.
    """

    class Device(models.TextChoices):
        """Device types for tracking."""

        DESKTOP = "desktop", "Desktop"
        MOBILE = "mobile", "Mobile"
        BOTH = "both", "Both"

    class AlertThreshold(models.TextChoices):
        """Alert sensitivity for ranking changes."""

        NONE = "none", "No Alerts"
        SMALL = "small", "3+ Position Changes"
        MEDIUM = "medium", "5+ Position Changes"
        LARGE = "large", "10+ Position Changes"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    keyword = models.ForeignKey(
        "seo.Keyword",
        on_delete=models.CASCADE,
        related_name="serp_tracking",
        help_text="Tracked keyword",
    )
    target_url = models.URLField(
        max_length=2048, blank=True, help_text="Expected ranking URL"
    )

    # Tracking config
    locations_json = models.JSONField(
        default=list, blank=True, help_text="ISO country codes to track"
    )
    device = models.CharField(
        max_length=16, choices=Device.choices, default=Device.BOTH
    )
    alert_threshold = models.CharField(
        max_length=16,
        choices=AlertThreshold.choices,
        default=AlertThreshold.MEDIUM,
    )
    is_active = models.BooleanField(default=True, db_index=True)

    # Current snapshot
    current_position = models.PositiveIntegerField(null=True, blank=True)
    previous_position = models.PositiveIntegerField(null=True, blank=True)
    position_change = models.IntegerField(default=0)
    current_url = models.URLField(max_length=2048, blank=True)
    serp_features_json = models.JSONField(
        default=list, blank=True, help_text="Detected SERP features"
    )

    # Last check
    last_checked_at = models.DateTimeField(null=True, blank=True)
    check_count = models.PositiveIntegerField(default=0)
    best_position = models.PositiveIntegerField(null=True, blank=True)
    worst_position = models.PositiveIntegerField(null=True, blank=True)

    metadata_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "voyager_serp_tracking"
        verbose_name = "SERP Tracking"
        verbose_name_plural = "SERP Trackings"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "keyword_id"]),
            models.Index(fields=["tenant_id", "is_active"]),
            models.Index(fields=["tenant_id", "-last_checked_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.keyword.keyword} (pos={self.current_position})"


class RankHistory(models.Model):
    """A historical rank snapshot for a tracked keyword.

    Stores position, URL, SERP features, and device info for
    each rank check to enable trend analysis.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tracking = models.ForeignKey(
        SERPTracking,
        on_delete=models.CASCADE,
        related_name="history",
        help_text="Parent tracking entry",
    )
    keyword_text = models.CharField(max_length=500, db_index=True)
    position = models.PositiveIntegerField(null=True, blank=True)
    previous_position = models.PositiveIntegerField(null=True, blank=True)
    position_change = models.IntegerField(default=0)
    url = models.URLField(max_length=2048, blank=True)
    serp_features_json = models.JSONField(default=list, blank=True)
    location = models.CharField(max_length=10, default="US")
    device = models.CharField(max_length=16, default="desktop")
    search_volume = models.PositiveIntegerField(null=True, blank=True)

    # Competitor data
    competitors_json = models.JSONField(
        default=list, blank=True, help_text="Top 10 competitor URLs and positions"
    )

    # Page metrics
    page_title = models.TextField(blank=True)
    page_description = models.TextField(blank=True)

    tracked_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "voyager_rank_history"
        verbose_name = "Rank History"
        verbose_name_plural = "Rank History"
        ordering = ["-tracked_at"]
        indexes = [
            models.Index(fields=["tracking", "-tracked_at"]),
            models.Index(fields=["keyword_text", "location", "device", "-tracked_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.keyword_text} pos={self.position} @{self.tracked_at.isoformat()}"
