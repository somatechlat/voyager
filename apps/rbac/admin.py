"""Django Admin for RBAC (Role-Based Access Control) app.

Registers Role, Permission, RoleAssignment, and Workspace models
with full list display, filters, search, and readonly fields.
"""

from __future__ import annotations

import json

from django.contrib import admin

from apps.rbac.models import Permission, Role, RoleAssignment, Workspace


class _JSONMixin:
    """Mixin for formatting JSON fields in admin list views."""

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


@admin.register(Role)
class RoleAdmin(_JSONMixin, admin.ModelAdmin):
    """Admin for Role model."""

    list_display = (
        "name",
        "level",
        "is_system",
        "tenant_id",
        "created_at",
        "updated_at",
    )
    list_filter = ("level", "is_system", "created_at")
    search_fields = ("name", "description", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")

    def display_permissions(self, obj: Role) -> str:
        return self._format_json(obj.permissions_json, 300)

    display_permissions.short_description = "Permissions"  # type: ignore[attr-defined]


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """Admin for Permission model."""

    list_display = (
        "resource",
        "action",
        "scope",
        "is_system",
        "created_at",
    )
    list_filter = ("action", "scope", "is_system", "created_at")
    search_fields = ("resource", "description")
    ordering = ("resource", "action")
    readonly_fields = ("id", "created_at")


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(admin.ModelAdmin):
    """Admin for RoleAssignment model."""

    list_display = (
        "user_id_short",
        "role_name",
        "workspace_name",
        "tenant_id",
        "created_at",
    )
    list_filter = ("role__level", "workspace__tier", "created_at")
    search_fields = (
        "user_id",
        "role__name",
        "workspace__name",
        "tenant_id",
    )
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at")
    list_select_related = ("role", "workspace")

    @admin.display(description="User ID")
    def user_id_short(self, obj: RoleAssignment) -> str:
        return obj.user_id[:12] + "..." if len(obj.user_id) > 12 else obj.user_id

    @admin.display(description="Role")
    def role_name(self, obj: RoleAssignment) -> str:
        return obj.role.name if obj.role else "—"

    @admin.display(description="Workspace")
    def workspace_name(self, obj: RoleAssignment) -> str:
        return obj.workspace.name if obj.workspace else "—"


@admin.register(Workspace)
class WorkspaceAdmin(_JSONMixin, admin.ModelAdmin):
    """Admin for Workspace model."""

    list_display = (
        "name",
        "tier",
        "max_users",
        "is_active",
        "created_at",
    )
    list_filter = ("tier", "is_active", "created_at")
    search_fields = ("name", "description")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")
