"""Competitor monitoring models — change detection, DOM diff, visual diff."""

from __future__ import annotations

import uuid

from django.db import models


class CompetitorMonitor(models.Model):
    """A competitor website to monitor for changes.

    Attributes:
        id: UUID primary key.
        tenant_id: Tenant scope identifier.
        name: Human-readable competitor name.
        url: URL to monitor.
        check_interval_minutes: Minutes between checks.
        is_active: Whether monitoring is enabled.
        last_checked_at: Timestamp of last check.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=2048)
    check_interval_minutes = models.PositiveIntegerField(default=60)
    is_active = models.BooleanField(default=True, db_index=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ws_competitor_monitors"
        indexes = [
            models.Index(fields=["tenant_id", "is_active"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"CompetitorMonitor({self.name})"


class CompetitorSnapshot(models.Model):
    """A scraped snapshot of a competitor page for comparison.

    Attributes:
        id: UUID primary key.
        competitor: FK to CompetitorMonitor.
        url: The scraped URL.
        content_hash: SHA-256 hash of content_text for fast comparison.
        content_text: Extracted visible text.
        dom_structure: JSON representation of DOM tree structure.
        screenshot_path: S3 or file path to the page screenshot.
        prices: JSON list of extracted prices.
        products: JSON list of extracted product identifiers.
        scraped_at: When the snapshot was taken.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    competitor = models.ForeignKey(
        CompetitorMonitor,
        on_delete=models.CASCADE,
        related_name="snapshots",
    )
    url = models.URLField(max_length=2048)
    content_hash = models.CharField(max_length=64, db_index=True)
    content_text = models.TextField(blank=True, default="")
    dom_structure = models.JSONField(default=dict, blank=True)
    screenshot_path = models.CharField(max_length=1024, blank=True, default="")
    prices = models.JSONField(default=list, blank=True)
    products = models.JSONField(default=list, blank=True)
    scraped_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "ws_competitor_snapshots"
        indexes = [
            models.Index(fields=["competitor", "scraped_at"]),
        ]
        ordering = ["-scraped_at"]

    def __str__(self) -> str:
        return f"Snapshot({self.competitor.name}, {self.scraped_at})"


class CompetitorChange(models.Model):
    """A detected change between two competitor snapshots.

    Attributes:
        id: UUID primary key.
        competitor: FK to CompetitorMonitor.
        url: The URL where change was detected.
        change_type: Category of change (new_content, removed_content, etc.).
        change_details: JSON with specifics of the change.
        detected_at: When the change was identified.
    """

    class ChangeType(models.TextChoices):
        NEW_CONTENT = "new_content", "New Content"
        REMOVED_CONTENT = "removed_content", "Removed Content"
        MODIFIED_CONTENT = "modified_content", "Modified Content"
        LAYOUT_CHANGE = "layout_change", "Layout Change"
        PRICE_CHANGE = "price_change", "Price Change"
        NEW_PRODUCT = "new_product", "New Product"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    competitor = models.ForeignKey(
        CompetitorMonitor,
        on_delete=models.CASCADE,
        related_name="changes",
    )
    url = models.URLField(max_length=2048)
    change_type = models.CharField(max_length=30, choices=ChangeType.choices, db_index=True)
    change_details = models.JSONField(default=dict, blank=True)
    detected_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "ws_competitor_changes"
        indexes = [
            models.Index(fields=["competitor", "detected_at"]),
        ]
        ordering = ["-detected_at"]

    def __str__(self) -> str:
        return f"Change({self.competitor.name}, {self.change_type})"
