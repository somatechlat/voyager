"""Django Admin for Integrations app.

Registers PlatformConnection, WebhookEndpoint, WebhookDelivery,
and SyncLog models.
"""

from __future__ import annotations

import json

from django.contrib import admin

from apps.integrations.models import (
    OAuthToken,
    PlatformConnection,
    RateLimitStatus,
    SyncConflict,
    SyncLog,
    WebhookDelivery,
    WebhookEndpoint,
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


class OAuthTokenInline(admin.TabularInline):
    """Inline for OAuthToken within PlatformConnection."""

    model = OAuthToken
    extra = 0
    readonly_fields = ("id", "created_at", "updated_at")


class RateLimitInline(admin.TabularInline):
    """Inline for RateLimitStatus within PlatformConnection."""

    model = RateLimitStatus
    extra = 0
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(PlatformConnection)
class PlatformConnectionAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for PlatformConnection model."""

    list_display = (
        "name",
        "provider",
        "provider_type",
        "account_type",
        "status",
        "health_score",
        "rate_limit_hits",
        "last_synced_at",
        "tenant_id_short",
        "created_at",
    )
    list_filter = (
        "provider",
        "provider_type",
        "account_type",
        "status",
        "created_at",
    )
    search_fields = (
        "name",
        "account_id",
        "account_name",
        "tenant_id",
    )
    ordering = ("-updated_at",)
    readonly_fields = (
        "id",
        "health_score",
        "rate_limit_hits",
        "last_synced_at",
        "created_at",
        "updated_at",
    )
    inlines = [OAuthTokenInline, RateLimitInline]

    @admin.display(description="Settings")
    def display_settings(self, obj: PlatformConnection) -> str:
        return self._format_json(obj.settings_json, 200)

    @admin.display(description="Capabilities")
    def display_capabilities(self, obj: PlatformConnection) -> str:
        return self._format_json(obj.capabilities_json, 150)


@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(_TenantIdMixin, admin.ModelAdmin):
    """Admin for WebhookEndpoint model."""

    list_display = (
        "name",
        "provider",
        "event_type",
        "is_active",
        "delivery_count",
        "failure_count",
        "avg_latency_ms",
        "created_at",
    )
    list_filter = (
        "provider",
        "event_type",
        "is_active",
        "created_at",
    )
    search_fields = (
        "name",
        "url",
        "secret",
        "tenant_id",
    )
    ordering = ("-updated_at",)
    readonly_fields = (
        "id",
        "delivery_count",
        "failure_count",
        "success_rate",
        "avg_latency_ms",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Success Rate")
    def success_rate(self, obj: WebhookEndpoint) -> str:
        return f"{obj.success_rate:.1f}%"

    @admin.display(description="Filters")
    def display_filters(self, obj: WebhookEndpoint) -> str:
        return self._format_json(obj.filters_json, 200)


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(_JSONMixin, admin.ModelAdmin):
    """Admin for WebhookDelivery model."""

    list_display = (
        "endpoint_name",
        "event_type",
        "status_code",
        "is_retry",
        "retry_count",
        "latency_ms",
        "delivered_at",
    )
    list_filter = (
        "status_code",
        "is_retry",
        "delivered_at",
    )
    search_fields = (
        "event_type",
        "event_id",
        "endpoint__name",
    )
    ordering = ("-delivered_at",)
    readonly_fields = ("id", "delivered_at")
    date_hierarchy = "delivered_at"
    list_select_related = ("endpoint",)

    @admin.display(description="Endpoint")
    def endpoint_name(self, obj: WebhookDelivery) -> str:
        return obj.endpoint.name if obj.endpoint else "—"

    @admin.display(description="Request Body")
    def display_request(self, obj: WebhookDelivery) -> str:
        return self._format_json(obj.request_body, 200)

    @admin.display(description="Response Body")
    def display_response(self, obj: WebhookDelivery) -> str:
        return self._format_json(obj.response_body, 200)


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    """Admin for SyncLog model."""

    list_display = (
        "connection_name",
        "entity_type",
        "action",
        "status",
        "synced_at",
    )
    list_filter = (
        "entity_type",
        "action",
        "status",
        "synced_at",
    )
    search_fields = (
        "entity_type",
        "platform_entity_id",
        "connection__name",
    )
    ordering = ("-synced_at",)
    readonly_fields = ("id", "synced_at")
    date_hierarchy = "synced_at"
    list_select_related = ("connection",)

    @admin.display(description="Connection")
    def connection_name(self, obj: SyncLog) -> str:
        return obj.connection.name if obj.connection else "—"


@admin.register(SyncConflict)
class SyncConflictAdmin(admin.ModelAdmin):
    """Admin for SyncConflict model."""

    list_display = (
        "entity_type",
        "conflict_type",
        "resolution",
        "resolved",
        "created_at",
    )
    list_filter = (
        "conflict_type",
        "resolution",
        "resolved",
        "created_at",
    )
    search_fields = (
        "entity_type",
        "entity_id",
        "tenant_id",
    )
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")
