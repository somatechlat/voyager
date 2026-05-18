"""Django Admin for Web Scraping V2 app.

Registers ScrapeJob, CompetitorMonitor, PriceTrack,
TrendDetection, and SentimentScore models.
"""

from __future__ import annotations

import json

from django.contrib import admin

from apps.web_scraping_v2.models import (
    CompetitorChange,
    CompetitorMonitor,
    CompetitorSnapshot,
    PriceTrack,
    ScrapeJob,
    SentimentScore,
    TrendDetection,
)


class _JSONMixin:
    """Mixin for formatting JSON fields."""

    @staticmethod
    def _format_json(value: object, max_len: int = 200) -> str:
        if not value:
            return "—"
        if isinstance(value, (dict, list)):
            text = json.dumps(value, indent=2, default=str)
            if len(text) > max_len:
                return text[:max_len] + "..."
            return text
        return str(value)[:max_len]


class CompetitorSnapshotInline(admin.TabularInline):
    """Inline for CompetitorSnapshot."""

    model = CompetitorSnapshot
    extra = 0
    readonly_fields = ("id", "scraped_at")


class CompetitorChangeInline(admin.TabularInline):
    """Inline for CompetitorChange."""

    model = CompetitorChange
    extra = 0
    readonly_fields = ("id", "detected_at")


@admin.register(ScrapeJob)
class ScrapeJobAdmin(_JSONMixin, admin.ModelAdmin):
    """Admin for ScrapeJob model."""

    list_display = (
        "url_preview",
        "status",
        "proxy_used",
        "started_at",
        "completed_at",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("url", "selector", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "started_at", "completed_at", "created_at", "updated_at")

    @admin.display(description="URL")
    def url_preview(self, obj: ScrapeJob) -> str:
        return obj.url[:60] + "..." if len(obj.url) > 60 else obj.url

    @admin.display(description="Metadata")
    def display_metadata(self, obj: ScrapeJob) -> str:
        return self._format_json(obj.metadata, 300)


@admin.register(CompetitorMonitor)
class CompetitorMonitorAdmin(admin.ModelAdmin):
    """Admin for CompetitorMonitor model."""

    list_display = (
        "name",
        "url",
        "check_interval_minutes",
        "is_active",
        "last_checked_at",
        "created_at",
    )
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "url", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [CompetitorSnapshotInline, CompetitorChangeInline]


@admin.register(PriceTrack)
class PriceTrackAdmin(admin.ModelAdmin):
    """Admin for PriceTrack model."""

    list_display = (
        "competitor_name",
        "product_name",
        "price",
        "currency",
        "discount_pct",
        "normalized_price",
        "extraction_source",
        "tracked_at",
    )
    list_filter = ("currency", "extraction_source", "tracked_at")
    search_fields = ("competitor_name", "product_name", "product_url", "tenant_id")
    ordering = ("-tracked_at",)
    readonly_fields = ("id", "tracked_at", "created_at")

    @admin.display(description="Product")
    def product_name_preview(self, obj: PriceTrack) -> str:
        return obj.product_name[:40] + "..." if len(obj.product_name) > 40 else obj.product_name


@admin.register(TrendDetection)
class TrendDetectionAdmin(_JSONMixin, admin.ModelAdmin):
    """Admin for TrendDetection model."""

    list_display = (
        "topic",
        "source",
        "mention_count",
        "trend_score",
        "stage",
        "peak_date",
        "tracked_at",
    )
    list_filter = ("stage", "source", "tracked_at")
    search_fields = ("topic", "tenant_id")
    ordering = ("-tracked_at",)
    readonly_fields = ("id", "tracked_at", "created_at")

    @admin.display(description="Data Points")
    def display_data(self, obj: TrendDetection) -> str:
        return self._format_json(obj.data_points, 250)


@admin.register(SentimentScore)
class SentimentScoreAdmin(_JSONMixin, admin.ModelAdmin):
    """Admin for SentimentScore model."""

    list_display = (
        "overall_sentiment",
        "overall_score",
        "confidence",
        "model",
        "source_type",
        "language",
        "analyzed_at",
    )
    list_filter = (
        "overall_sentiment",
        "model",
        "source_type",
        "language",
        "analyzed_at",
    )
    search_fields = ("text", "source_id", "tenant_id")
    ordering = ("-analyzed_at",)
    readonly_fields = ("id", "text_hash", "analyzed_at", "created_at")

    @admin.display(description="Text Preview")
    def text_preview(self, obj: SentimentScore) -> str:
        return obj.text[:80] + "..." if len(obj.text) > 80 else obj.text

    @admin.display(description="Aspects")
    def display_aspects(self, obj: SentimentScore) -> str:
        return self._format_json(obj.aspects, 200)

    @admin.display(description="Emotions")
    def display_emotions(self, obj: SentimentScore) -> str:
        return self._format_json(obj.emotions, 200)
