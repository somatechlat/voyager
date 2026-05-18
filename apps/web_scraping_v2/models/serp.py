"""SERPTracking model — search engine rank and feature detection."""

from __future__ import annotations

import uuid

from django.db import models


class SERPTracking(models.Model):
    """A SERP ranking result for a tracked keyword.

    Tracks organic position, URL, title, description, detected SERP
    features, and position change over time.

    Attributes:
        id: UUID primary key.
        tenant_id: Tenant scope identifier.
        keyword: The tracked search keyword.
        location_country: ISO country code (e.g., US, GB).
        location_region: Region or state name.
        language: Language code (e.g., en, es).
        device: Device type (desktop or mobile).
        position: Organic ranking position (1-100+).
        url: The ranked page URL.
        title: Page title from SERP.
        description: Meta description from SERP.
        serp_features: JSON list of detected SERP features.
        position_change: Change in position since last check (+/-).
        search_volume: Estimated monthly search volume.
        cpc: Estimated cost-per-click in USD.
        competition: Competition level (low, medium, high).
        tracked_at: When the ranking was recorded.
        created_at: Record creation timestamp.
    """

    class Device(models.TextChoices):
        DESKTOP = "desktop", "Desktop"
        MOBILE = "mobile", "Mobile"
        TABLET = "tablet", "Tablet"

    class CompetitionLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    keyword = models.CharField(max_length=500, db_index=True)
    location_country = models.CharField(max_length=5, blank=True, default="")
    location_region = models.CharField(max_length=100, blank=True, default="")
    language = models.CharField(max_length=5, default="en")
    device = models.CharField(
        max_length=10,
        choices=Device.choices,
        default=Device.DESKTOP,
    )
    position = models.PositiveIntegerField(null=True, blank=True)
    url = models.URLField(max_length=2048, blank=True, default="")
    title = models.TextField(blank=True, default="")
    description = models.TextField(blank=True, default="")
    serp_features = models.JSONField(default=list, blank=True)
    position_change = models.IntegerField(default=0)
    search_volume = models.PositiveIntegerField(null=True, blank=True)
    cpc = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    competition = models.CharField(
        max_length=10,
        choices=CompetitionLevel.choices,
        blank=True,
        default="",
    )
    tracked_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ws_serp_trackings"
        indexes = [
            models.Index(fields=["tenant_id", "keyword", "tracked_at"]),
            models.Index(fields=["tenant_id", "device", "tracked_at"]),
            models.Index(fields=["position"]),
        ]
        ordering = ["-tracked_at"]

    def __str__(self) -> str:
        return f"SERP({self.keyword}, pos={self.position})"
