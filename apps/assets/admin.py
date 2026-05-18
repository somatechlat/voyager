"""Django Admin for Assets app.

Registers Asset, AssetFolder, AssetCollection, AssetVersion,
and AssetLicense models.
"""

from __future__ import annotations

import json

from django.contrib import admin

from apps.assets.models import (
    Asset,
    AssetCollection,
    AssetFolder,
    AssetLicense,
    AssetVersion,
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


class AssetVersionInline(admin.TabularInline):
    """Inline for AssetVersion within Asset."""

    model = AssetVersion
    extra = 0
    readonly_fields = ("id", "uploaded_at")


@admin.register(Asset)
class AssetAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for Asset model."""

    list_display = (
        "name",
        "asset_type",
        "file_type",
        "status",
        "size_mb",
        "dimensions",
        "duration_seconds",
        "ai_generated",
        "ai_tags_status",
        "usage_count",
        "tenant_id_short",
        "created_at",
    )
    list_filter = (
        "asset_type",
        "file_type",
        "status",
        "ai_generated",
        "ai_tags_status",
        "created_at",
    )
    search_fields = (
        "name",
        "description",
        "searchable_text",
        "ai_tags_json",
        "tenant_id",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "size_mb",
        "dimensions",
        "duration_seconds",
        "frame_count",
        "usage_count",
        "cdn_url",
        "processing_status",
        "created_at",
        "updated_at",
    )
    inlines = [AssetVersionInline]

    @admin.display(description="AI Tags")
    def display_tags(self, obj: Asset) -> str:
        return self._format_json(obj.ai_tags_json, 200)

    @admin.display(description="Colors")
    def display_colors(self, obj: Asset) -> str:
        return self._format_json(obj.colors_json, 150)

    @admin.display(description="Metadata")
    def display_metadata(self, obj: Asset) -> str:
        return self._format_json(obj.metadata_json, 200)

    @admin.display(description="EXIF")
    def display_exif(self, obj: Asset) -> str:
        return self._format_json(obj.exif_json, 150)


@admin.register(AssetFolder)
class AssetFolderAdmin(_TenantIdMixin, admin.ModelAdmin):
    """Admin for AssetFolder model."""

    list_display = (
        "name",
        "parent_name",
        "asset_count",
        "total_size_mb",
        "tenant_id_short",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("name", "tenant_id")
    ordering = ("name",)
    readonly_fields = ("id", "asset_count", "total_size_mb", "created_at", "updated_at")

    @admin.display(description="Parent")
    def parent_name(self, obj: AssetFolder) -> str:
        return obj.parent.name if obj.parent else "—"


@admin.register(AssetCollection)
class AssetCollectionAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for AssetCollection model."""

    list_display = (
        "name",
        "collection_type",
        "asset_count",
        "tenant_id_short",
        "created_at",
    )
    list_filter = ("collection_type", "created_at")
    search_fields = ("name", "description", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "asset_count", "created_at", "updated_at")

    @admin.display(description="Filters")
    def display_filters(self, obj: AssetCollection) -> str:
        return self._format_json(obj.smart_filters_json, 200)


@admin.register(AssetVersion)
class AssetVersionAdmin(admin.ModelAdmin):
    """Admin for AssetVersion model."""

    list_display = (
        "asset_name",
        "version_number",
        "change_summary",
        "file_size_mb",
        "is_current",
        "uploaded_by",
        "uploaded_at",
    )
    list_filter = (
        "is_current",
        "uploaded_at",
    )
    search_fields = (
        "change_summary",
        "asset__name",
    )
    ordering = ("-version_number",)
    readonly_fields = ("id", "file_size_mb", "uploaded_at")
    list_select_related = ("asset",)

    @admin.display(description="Asset")
    def asset_name(self, obj: AssetVersion) -> str:
        return obj.asset.name if obj.asset else "—"


@admin.register(AssetLicense)
class AssetLicenseAdmin(admin.ModelAdmin):
    """Admin for AssetLicense model."""

    list_display = (
        "asset_name",
        "license_type",
        "licensor",
        "cost",
        "currency",
        "license_scope",
        "usage_limit",
        "current_usage",
        "valid_from",
        "valid_until",
        "is_perpetual",
        "is_active",
        "auto_renew",
    )
    list_filter = (
        "license_type",
        "license_scope",
        "is_perpetual",
        "is_active",
        "auto_renew",
        "valid_from",
        "valid_until",
    )
    search_fields = (
        "licensor",
        "license_url",
        "terms_text",
        "asset__name",
    )
    ordering = ("-valid_from",)
    readonly_fields = ("id", "current_usage", "created_at", "updated_at")
    date_hierarchy = "valid_from"
    list_select_related = ("asset",)

    @admin.display(description="Asset")
    def asset_name(self, obj: AssetLicense) -> str:
        return obj.asset.name if obj.asset else "—"

    @admin.display(description="Territories")
    def display_territories(self, obj: AssetLicense) -> str:
        return self._format_json(obj.territories_json, 150)

    @admin.display(description="Prohibited Uses")
    def display_prohibited(self, obj: AssetLicense) -> str:
        return self._format_json(obj.prohibited_uses_json, 150)
