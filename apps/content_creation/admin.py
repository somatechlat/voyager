"""Django Admin for Content Creation app.

Registers ContentGeneration, BrandKit, ContentTemplate, ABTest,
and RevisionHistory models with full admin configuration.
"""

from __future__ import annotations

import json

from django.contrib import admin

from apps.content_creation.models import (
    ABTest,
    BrandKit,
    ContentGeneration,
    ContentTemplate,
    RevisionHistory,
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


@admin.register(ContentGeneration)
class ContentGenerationAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for ContentGeneration model."""

    list_display = (
        "title",
        "content_type",
        "status",
        "quality_score",
        "tenant_id_short",
        "created_at",
    )
    list_filter = ("content_type", "status", "tone", "created_at")
    search_fields = ("title", "body_text", "keywords_json", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "word_count",
        "char_count",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Keywords")
    def display_keywords(self, obj: ContentGeneration) -> str:
        return self._format_json(obj.keywords_json, 150)

    @admin.display(description="Sections")
    def display_sections(self, obj: ContentGeneration) -> str:
        return self._format_json(obj.sections_json, 200)


@admin.register(BrandKit)
class BrandKitAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for BrandKit model."""

    list_display = (
        "name",
        "tenant_id_short",
        "is_default",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_default", "created_at")
    search_fields = ("name", "description", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")

    @admin.display(description="Colors")
    def display_colors(self, obj: BrandKit) -> str:
        return self._format_json(obj.colors, 200)

    @admin.display(description="Fonts")
    def display_fonts(self, obj: BrandKit) -> str:
        return self._format_json(obj.fonts, 200)

    @admin.display(description="Logos")
    def display_logos(self, obj: BrandKit) -> str:
        return self._format_json(obj.logos, 200)

    @admin.display(description="Voice")
    def display_voice(self, obj: BrandKit) -> str:
        return self._format_json(obj.voice, 200)


@admin.register(ContentTemplate)
class ContentTemplateAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for ContentTemplate model."""

    list_display = (
        "name",
        "category",
        "content_type",
        "usage_count",
        "is_public",
        "tenant_id_short",
        "created_at",
    )
    list_filter = ("category", "content_type", "is_public", "created_at")
    search_fields = ("name", "description", "body", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "usage_count", "created_at", "updated_at")

    @admin.display(description="Variables")
    def display_variables(self, obj: ContentTemplate) -> str:
        return self._format_json(obj.variables, 200)

    @admin.display(description="Defaults")
    def display_defaults(self, obj: ContentTemplate) -> str:
        return self._format_json(obj.default_values, 200)


@admin.register(ABTest)
class ABTestAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for ABTest model."""

    list_display = (
        "name",
        "status",
        "winner_criteria",
        "start_date",
        "end_date",
        "sample_size",
        "tenant_id_short",
        "created_at",
    )
    list_filter = ("status", "winner_criteria", "created_at")
    search_fields = ("name", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at")
    date_hierarchy = "created_at"

    @admin.display(description="Variants")
    def display_variants(self, obj: ABTest) -> str:
        return self._format_json(obj.variants, 300)

    @admin.display(description="Results")
    def display_results(self, obj: ABTest) -> str:
        return self._format_json(obj.results, 300)


@admin.register(RevisionHistory)
class RevisionHistoryAdmin(_JSONMixin, admin.ModelAdmin):
    """Admin for RevisionHistory model."""

    list_display = (
        "content_generation_id_short",
        "version_number",
        "change_summary",
        "changed_by_short",
        "created_at",
    )
    list_filter = ("version_number", "created_at")
    search_fields = (
        "content_generation_id",
        "body_text",
        "change_summary",
        "changed_by",
    )
    ordering = ("-version_number",)
    readonly_fields = ("id", "created_at")

    @admin.display(description="Content ID")
    def content_generation_id_short(self, obj: RevisionHistory) -> str:
        cid = str(obj.content_generation_id)
        return cid[:12] + "..." if len(cid) > 12 else cid

    @admin.display(description="Changed By")
    def changed_by_short(self, obj: RevisionHistory) -> str:
        return obj.changed_by[:12] + "..." if len(obj.changed_by) > 12 else obj.changed_by

    @admin.display(description="Diff")
    def display_diff(self, obj: RevisionHistory) -> str:
        return self._format_json(obj.diff_json, 300)
