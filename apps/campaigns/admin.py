"""Django Admin for Campaigns app.

Registers Campaign, CampaignChannel, CampaignABTest, CampaignBudget,
and CampaignPerformance models.
"""

from __future__ import annotations

import json

from django.contrib import admin

from apps.campaigns.models import (
    Campaign,
    CampaignABTest,
    CampaignBudget,
    CampaignChannel,
    CampaignPerformance,
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


@admin.register(Campaign)
class CampaignAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for Campaign model."""

    list_display = (
        "name",
        "status",
        "goal",
        "start_date",
        "end_date",
        "tenant_id_short",
        "created_at",
    )
    list_filter = ("status", "goal", "start_date", "created_at")
    search_fields = ("name", "description", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")
    date_hierarchy = "start_date"

    @admin.display(description="Audience")
    def display_audience(self, obj: Campaign) -> str:
        return self._format_json(obj.audience_targeting, 200)

    @admin.display(description="Channels")
    def display_channels(self, obj: Campaign) -> str:
        return self._format_json(obj.channel_ids, 150)


@admin.register(CampaignChannel)
class CampaignChannelAdmin(_TenantIdMixin, admin.ModelAdmin):
    """Admin for CampaignChannel model."""

    list_display = (
        "name",
        "channel_type",
        "platform",
        "account_handle",
        "is_primary",
        "is_active",
        "tenant_id_short",
        "created_at",
    )
    list_filter = ("channel_type", "platform", "is_primary", "is_active", "created_at")
    search_fields = ("name", "account_handle", "platform_id", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(CampaignABTest)
class CampaignABTestAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for CampaignABTest model."""

    list_display = (
        "name",
        "campaign_name",
        "status",
        "test_type",
        "winner_metric",
        "tenant_id_short",
        "created_at",
    )
    list_filter = ("status", "test_type", "winner_metric", "created_at")
    search_fields = ("name", "campaign_id", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")
    list_select_related = ("campaign",)

    @admin.display(description="Campaign")
    def campaign_name(self, obj: CampaignABTest) -> str:
        return obj.campaign.name if obj.campaign else obj.campaign_id[:12]

    @admin.display(description="Variants")
    def display_variants(self, obj: CampaignABTest) -> str:
        return self._format_json(obj.variants, 300)

    @admin.display(description="Results")
    def display_results(self, obj: CampaignABTest) -> str:
        return self._format_json(obj.results, 300)


@admin.register(CampaignBudget)
class CampaignBudgetAdmin(_TenantIdMixin, admin.ModelAdmin):
    """Admin for CampaignBudget model."""

    list_display = (
        "campaign_name",
        "total_budget",
        "daily_cap",
        "spent",
        "remaining",
        "currency",
        "tenant_id_short",
        "created_at",
    )
    list_filter = ("currency", "created_at")
    search_fields = ("campaign_id", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "spent", "remaining", "created_at", "updated_at")
    list_select_related = ("campaign",)

    @admin.display(description="Campaign")
    def campaign_name(self, obj: CampaignBudget) -> str:
        return obj.campaign.name if obj.campaign else obj.campaign_id[:12]


@admin.register(CampaignPerformance)
class CampaignPerformanceAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for CampaignPerformance model."""

    list_display = (
        "campaign_name",
        "date",
        "impressions",
        "clicks",
        "conversions",
        "spend",
        "tenant_id_short",
    )
    list_filter = ("date", "created_at")
    search_fields = ("campaign_id", "tenant_id")
    ordering = ("-date",)
    readonly_fields = ("id", "created_at", "updated_at")
    date_hierarchy = "date"
    list_select_related = ("campaign",)

    @admin.display(description="Campaign")
    def campaign_name(self, obj: CampaignPerformance) -> str:
        return obj.campaign.name if obj.campaign else obj.campaign_id[:12]

    @admin.display(description="Platform Breakdown")
    def display_breakdown(self, obj: CampaignPerformance) -> str:
        return self._format_json(obj.platform_breakdown, 200)

    @admin.display(description="Top Creative")
    def display_creative(self, obj: CampaignPerformance) -> str:
        return self._format_json(obj.top_creative_ids, 150)
