"""Django Admin for SEO app.

Registers Keyword, OnPageAudit, Backlink, TechnicalCrawl,
and ContentOptimization models.
"""

from __future__ import annotations

import json

from django.contrib import admin

from apps.seo.models import (
    Backlink,
    ContentOptimization,
    Keyword,
    KeywordCluster,
    OnPageAudit,
    TechnicalCrawl,
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


class _TenantIdMixin:
    """Mixin for shortening tenant_id display."""

    @admin.display(description="Tenant")
    def tenant_id_short(self, obj):
        tid = getattr(obj, "tenant_id", "")
        return tid[:12] + "..." if len(str(tid)) > 12 else str(tid)


class KeywordInline(admin.TabularInline):
    """Inline for Keyword within KeywordCluster."""

    model = Keyword
    extra = 0
    fields = (
        "keyword",
        "monthly_volume",
        "difficulty",
        "current_position",
        "opportunity_score",
    )
    readonly_fields = fields


@admin.register(KeywordCluster)
class KeywordClusterAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for KeywordCluster model."""

    list_display = (
        "label",
        "total_volume",
        "avg_difficulty",
        "priority_score",
        "keyword_count",
        "tenant_id_short",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("label", "tenant_id")
    ordering = ("-priority_score",)
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [KeywordInline]

    @admin.display(description="Keywords")
    def keyword_count(self, obj: KeywordCluster) -> int:
        return obj.keywords.count()


@admin.register(Keyword)
class KeywordAdmin(_TenantIdMixin, admin.ModelAdmin):
    """Admin for Keyword model."""

    list_display = (
        "keyword",
        "location",
        "language",
        "monthly_volume",
        "difficulty",
        "cpc",
        "trend_direction",
        "current_position",
        "opportunity_score",
        "commercial_intent",
        "is_tracked",
        "tenant_id_short",
    )
    list_filter = (
        "trend_direction",
        "commercial_intent",
        "is_tracked",
        "location",
        "language",
        "created_at",
    )
    search_fields = ("keyword", "target_url", "tenant_id")
    ordering = ("-opportunity_score",)
    readonly_fields = ("id", "created_at", "updated_at")
    list_select_related = ("cluster",)
    date_hierarchy = "created_at"


@admin.register(OnPageAudit)
class OnPageAuditAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for OnPageAudit model."""

    list_display = (
        "url_preview",
        "score",
        "grade",
        "title_length",
        "word_count",
        "readability_score",
        "internal_links",
        "images_total",
        "audited_at",
    )
    list_filter = ("grade", "audited_at")
    search_fields = ("url", "title", "meta_description", "h1", "tenant_id")
    ordering = ("-audited_at",)
    readonly_fields = ("id", "audited_at", "updated_at")
    date_hierarchy = "audited_at"

    @admin.display(description="URL")
    def url_preview(self, obj: OnPageAudit) -> str:
        return obj.url[:60] + "..." if len(obj.url) > 60 else obj.url

    @admin.display(description="Issues")
    def display_issues(self, obj: OnPageAudit) -> str:
        return self._format_json(obj.issues_json, 200)

    @admin.display(description="Recommendations")
    def display_recommendations(self, obj: OnPageAudit) -> str:
        return self._format_json(obj.recommendations_json, 200)


@admin.register(Backlink)
class BacklinkAdmin(_TenantIdMixin, admin.ModelAdmin):
    """Admin for Backlink model."""

    list_display = (
        "referring_domain",
        "target_url_preview",
        "anchor_text_preview",
        "domain_authority",
        "page_authority",
        "spam_score",
        "is_toxic",
        "link_type",
        "status",
        "created_at",
    )
    list_filter = (
        "link_type",
        "status",
        "is_toxic",
        "is_sitewide",
        "created_at",
    )
    search_fields = (
        "source_url",
        "target_url",
        "anchor_text",
        "referring_domain",
        "tenant_id",
    )
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")

    @admin.display(description="Target URL")
    def target_url_preview(self, obj: Backlink) -> str:
        return obj.target_url[:50] + "..." if len(obj.target_url) > 50 else obj.target_url

    @admin.display(description="Anchor")
    def anchor_text_preview(self, obj: Backlink) -> str:
        return obj.anchor_text[:30] if obj.anchor_text else "—"


@admin.register(TechnicalCrawl)
class TechnicalCrawlAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for TechnicalCrawl model."""

    list_display = (
        "url_preview",
        "status_code",
        "is_indexable",
        "word_count",
        "page_size_kb",
        "load_time_ms",
        "seo_score",
        "is_mobile_friendly",
        "crawled_at",
    )
    list_filter = (
        "status_code",
        "is_indexable",
        "is_mobile_friendly",
        "crawled_at",
    )
    search_fields = ("url", "title", "tenant_id", "crawl_job_id")
    ordering = ("-crawled_at",)
    readonly_fields = ("id", "crawled_at", "updated_at")
    date_hierarchy = "crawled_at"

    @admin.display(description="URL")
    def url_preview(self, obj: TechnicalCrawl) -> str:
        return obj.url[:60] + "..." if len(obj.url) > 60 else obj.url

    @admin.display(description="Issues")
    def display_issues(self, obj: TechnicalCrawl) -> str:
        return self._format_json(obj.issues_json, 200)

    @admin.display(description="CWV")
    def display_cwv(self, obj: TechnicalCrawl) -> str:
        parts = []
        if obj.lcp_ms:
            parts.append(f"LCP={obj.lcp_ms}ms")
        if obj.fid_ms:
            parts.append(f"FID={obj.fid_ms}ms")
        if obj.cls_score:
            parts.append(f"CLS={obj.cls_score}")
        return " | ".join(parts) if parts else "—"


@admin.register(ContentOptimization)
class ContentOptimizationAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for ContentOptimization model."""

    list_display = (
        "url_preview",
        "word_count",
        "content_score",
        "readability_score",
        "seo_score",
        "uniqueness_score",
        "analyzed_at",
    )
    list_filter = ("analyzed_at",)
    search_fields = ("url", "content_hash", "tenant_id")
    ordering = ("-analyzed_at",)
    readonly_fields = ("id", "analyzed_at", "updated_at")
    date_hierarchy = "analyzed_at"

    @admin.display(description="URL")
    def url_preview(self, obj: ContentOptimization) -> str:
        return obj.url[:60] + "..." if len(obj.url) > 60 else obj.url

    @admin.display(description="Keywords")
    def display_keywords(self, obj: ContentOptimization) -> str:
        return self._format_json(obj.keyword_density_json, 200)

    @admin.display(description="Recommendations")
    def display_recs(self, obj: ContentOptimization) -> str:
        return self._format_json(obj.recommendations_json, 200)
