"""Django Admin for Audit app.

Registers AuditLogEntry and AuditLogArchive models with hash chain
integrity display, filtering, and search capabilities.
"""

from __future__ import annotations

import json

from django.contrib import admin

from apps.audit.models import AuditLogArchive, AuditLogEntry


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


@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(_JSONMixin, admin.ModelAdmin):
    """Admin for AuditLogEntry with hash chain verification display."""

    list_display = (
        "id",
        "timestamp",
        "actor_type",
        "action",
        "resource_type",
        "outcome",
        "tenant_id_short",
    )
    list_filter = (
        "actor_type",
        "outcome",
        "action",
        "resource_type",
        "timestamp",
    )
    search_fields = (
        "actor_id",
        "actor_email",
        "action",
        "resource_type",
        "resource_id",
        "tenant_id",
        "request_id",
    )
    ordering = ("-timestamp",)
    readonly_fields = (
        "id",
        "timestamp",
        "previous_hash",
        "entry_hash",
        "display_details",
    )
    date_hierarchy = "timestamp"

    @admin.display(description="Tenant")
    def tenant_id_short(self, obj: AuditLogEntry) -> str:
        return obj.tenant_id[:12] + "..." if len(obj.tenant_id) > 12 else obj.tenant_id

    @admin.display(description="Details")
    def display_details(self, obj: AuditLogEntry) -> str:
        return self._format_json(obj.details, 500)

    def has_delete_permission(self, request, obj=None):
        """Audit logs are immutable — deletion is not permitted."""
        return False


@admin.register(AuditLogArchive)
class AuditLogArchiveAdmin(admin.ModelAdmin):
    """Admin for AuditLogArchive (read-only compressed archives)."""

    list_display = (
        "year_month",
        "tenant_id_short",
        "log_count",
        "created_at",
    )
    list_filter = ("year_month", "created_at")
    search_fields = ("tenant_id", "year_month")
    ordering = ("-year_month", "tenant_id")
    readonly_fields = (
        "id",
        "year_month",
        "tenant_id",
        "log_count",
        "archive_data",
        "created_at",
    )
    date_hierarchy = "created_at"

    @admin.display(description="Tenant")
    def tenant_id_short(self, obj: AuditLogArchive) -> str:
        return obj.tenant_id[:12] + "..." if len(obj.tenant_id) > 12 else obj.tenant_id

    def has_add_permission(self, request):
        """Archives are created by the archival system, not via admin."""
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
