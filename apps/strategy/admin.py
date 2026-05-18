"""Django Admin for Strategy app.

Registers AudiencePersona, CompetitorProfile, ContentStrategy,
EditorialCalendar, and OKRTracking models.
"""

from __future__ import annotations

import json

from django.contrib import admin

from apps.strategy.models import (
    AudiencePersona,
    CompetitorContent,
    CompetitorProfile,
    ContentStrategy,
    EditorialCalendar,
    KeyResult,
    Objective,
    PersonaCampaignLink,
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


class PersonaCampaignLinkInline(admin.TabularInline):
    """Inline for PersonaCampaignLink."""

    model = PersonaCampaignLink
    extra = 0
    readonly_fields = ("id", "created_at", "updated_at")


class CompetitorContentInline(admin.TabularInline):
    """Inline for CompetitorContent."""

    model = CompetitorContent
    extra = 0
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(AudiencePersona)
class AudiencePersonaAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for AudiencePersona model."""

    list_display = (
        "name",
        "is_active",
        "tenant_id_short",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "description", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [PersonaCampaignLinkInline]

    @admin.display(description="Demographics")
    def display_demographics(self, obj: AudiencePersona) -> str:
        return self._format_json(obj.demographics, 200)

    @admin.display(description="Psychographics")
    def display_psychographics(self, obj: AudiencePersona) -> str:
        return self._format_json(obj.psychographics, 200)

    @admin.display(description="Pain Points")
    def display_pain_points(self, obj: AudiencePersona) -> str:
        return self._format_json(obj.pain_points, 200)

    @admin.display(description="Content Prefs")
    def display_content_prefs(self, obj: AudiencePersona) -> str:
        return self._format_json(obj.content_preferences, 200)


@admin.register(CompetitorProfile)
class CompetitorProfileAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for CompetitorProfile model."""

    list_display = (
        "name",
        "website",
        "is_active",
        "last_scraped_at",
        "tenant_id_short",
        "created_at",
    )
    list_filter = ("is_active", "last_scraped_at", "created_at")
    search_fields = ("name", "website", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [CompetitorContentInline]

    @admin.display(description="Social Profiles")
    def display_social(self, obj: CompetitorProfile) -> str:
        return self._format_json(obj.social_profiles, 200)

    @admin.display(description="SWOT")
    def display_swot(self, obj: CompetitorProfile) -> str:
        return self._format_json(obj.swot_analysis, 300)


@admin.register(ContentStrategy)
class ContentStrategyAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for ContentStrategy model."""

    list_display = (
        "name",
        "goal",
        "tenant_id_short",
        "created_at",
        "updated_at",
    )
    list_filter = ("goal", "created_at")
    search_fields = ("name", "tenant_id")
    ordering = ("-updated_at",)
    readonly_fields = ("id", "created_at", "updated_at")

    @admin.display(description="Topic Clusters")
    def display_topics(self, obj: ContentStrategy) -> str:
        return self._format_json(obj.topic_clusters, 250)

    @admin.display(description="Format Mix")
    def display_format_mix(self, obj: ContentStrategy) -> str:
        return self._format_json(obj.format_mix, 200)

    @admin.display(description="Channels")
    def display_channels(self, obj: ContentStrategy) -> str:
        return self._format_json(obj.channel_allocation, 200)

    @admin.display(description="Pillars")
    def display_pillars(self, obj: ContentStrategy) -> str:
        return self._format_json(obj.content_pillars, 200)

    @admin.display(description="Gap Analysis")
    def display_gaps(self, obj: ContentStrategy) -> str:
        return self._format_json(obj.gap_analysis, 250)


@admin.register(EditorialCalendar)
class EditorialCalendarAdmin(_TenantIdMixin, admin.ModelAdmin):
    """Admin for EditorialCalendar model."""

    list_display = (
        "title",
        "content_type",
        "platform",
        "status",
        "priority",
        "publish_date",
        "due_date",
        "tenant_id_short",
    )
    list_filter = ("content_type", "platform", "status", "priority", "publish_date")
    search_fields = ("title", "notes", "tenant_id")
    ordering = ("publish_date", "priority")
    readonly_fields = ("id", "created_at", "updated_at")
    date_hierarchy = "publish_date"
    list_select_related = ("strategy",)


class KeyResultInline(admin.TabularInline):
    """Inline for KeyResult within Objective."""

    model = KeyResult
    extra = 0
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Objective)
class ObjectiveAdmin(_TenantIdMixin, admin.ModelAdmin):
    """Admin for Objective (OKR) model."""

    list_display = (
        "title_preview",
        "level",
        "quarter",
        "status",
        "progress_display",
        "tenant_id_short",
        "created_at",
    )
    list_filter = ("level", "status", "quarter", "created_at")
    search_fields = ("title", "description", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [KeyResultInline]

    @admin.display(description="Title")
    def title_preview(self, obj: Objective) -> str:
        return obj.title[:60] + "..." if len(obj.title) > 60 else obj.title

    @admin.display(description="Progress")
    def progress_display(self, obj: Objective) -> str:
        return f"{obj.progress}%"


@admin.register(KeyResult)
class KeyResultAdmin(admin.ModelAdmin):
    """Admin for KeyResult model."""

    list_display = (
        "title_preview",
        "objective_title",
        "kr_type",
        "current_value",
        "target_value",
        "unit",
        "confidence",
        "created_at",
    )
    list_filter = ("kr_type", "direction", "confidence", "created_at")
    search_fields = ("title", "unit")
    ordering = ("created_at",)
    readonly_fields = ("id", "created_at", "updated_at")
    list_select_related = ("objective",)

    @admin.display(description="Title")
    def title_preview(self, obj: KeyResult) -> str:
        return obj.title[:60] + "..." if len(obj.title) > 60 else obj.title

    @admin.display(description="Objective")
    def objective_title(self, obj: KeyResult) -> str:
        title = obj.objective.title
        return title[:40] + "..." if len(title) > 40 else title
