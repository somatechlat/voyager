"""Django Admin for Clients app.

Registers Client, ClientContact, Project, ProjectMilestone,
and CommunicationLog models.
"""

from __future__ import annotations

import json

from django.contrib import admin

from apps.clients.models import (
    Client,
    ClientContact,
    CommunicationLog,
    Project,
    ProjectMilestone,
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


class ClientContactInline(admin.TabularInline):
    """Inline for ClientContact within Client."""

    model = ClientContact
    extra = 0
    readonly_fields = ("id", "created_at")


class ProjectMilestoneInline(admin.TabularInline):
    """Inline for ProjectMilestone within Project."""

    model = ProjectMilestone
    extra = 0
    readonly_fields = ("id", "created_at", "updated_at")


class CommunicationLogInline(admin.TabularInline):
    """Inline for CommunicationLog within Client."""

    model = CommunicationLog
    extra = 0
    readonly_fields = ("id", "created_at")


@admin.register(Client)
class ClientAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for Client model."""

    list_display = (
        "name",
        "status",
        "industry",
        "lifecycle_stage",
        "nrr",
        "health_score",
        "total_contract_value",
        "mrr",
        "csat_score",
        "nps_score",
        "churn_risk_score",
        "next_check_in",
        "tenant_id_short",
    )
    list_filter = (
        "status",
        "industry",
        "lifecycle_stage",
        "created_at",
    )
    search_fields = (
        "name",
        "website",
        "address",
        "notes",
        "tenant_id",
    )
    ordering = ("-created_at",)
    readonly_fields = ("id", "total_contract_value", "mrr", "created_at", "updated_at")
    inlines = [ClientContactInline, CommunicationLogInline]

    @admin.display(description="Products")
    def display_products(self, obj: Client) -> str:
        return self._format_json(obj.products_purchased, 200)

    @admin.display(description="Tech Stack")
    def display_tech(self, obj: Client) -> str:
        return self._format_json(obj.tech_stack, 150)

    @admin.display(description="ICP Fit")
    def display_icp(self, obj: Client) -> str:
        return self._format_json(obj.icp_fit_score, 150)

    @admin.display(description="PQL Signals")
    def display_pql(self, obj: Client) -> str:
        return self._format_json(obj.pql_signals, 150)


@admin.register(ClientContact)
class ClientContactAdmin(admin.ModelAdmin):
    """Admin for ClientContact model."""

    list_display = (
        "name",
        "email",
        "phone",
        "role",
        "is_primary",
        "is_billing",
        "is_technical",
        "is_decision_maker",
        "last_engaged_at",
        "created_at",
    )
    list_filter = (
        "role",
        "is_primary",
        "is_billing",
        "is_technical",
        "is_decision_maker",
        "created_at",
    )
    search_fields = ("name", "email", "phone", "notes")
    ordering = ("-created_at",)
    readonly_fields = ("id", "last_engaged_at", "created_at", "updated_at")
    list_select_related = ("client",)

    @admin.display(description="Client")
    def client_name(self, obj: ClientContact) -> str:
        return obj.client.name if obj.client else "—"


@admin.register(Project)
class ProjectAdmin(_JSONMixin, admin.ModelAdmin):
    """Admin for Project model."""

    list_display = (
        "name",
        "status",
        "priority",
        "budget",
        "spent",
        "completion_pct",
        "start_date",
        "due_date",
        "actual_end_date",
        "is_billable",
        "total_logged_hours",
        "created_at",
    )
    list_filter = (
        "status",
        "priority",
        "is_billable",
        "start_date",
        "created_at",
    )
    search_fields = (
        "name",
        "description",
        "client__name",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "spent",
        "completion_pct",
        "total_logged_hours",
        "profitability_score",
        "created_at",
        "updated_at",
    )
    inlines = [ProjectMilestoneInline]
    list_select_related = ("client",)
    date_hierarchy = "start_date"

    @admin.display(description="SOW")
    def display_sow(self, obj: Project) -> str:
        return self._format_json(obj.sow, 200)


@admin.register(ProjectMilestone)
class ProjectMilestoneAdmin(admin.ModelAdmin):
    """Admin for ProjectMilestone model."""

    list_display = (
        "name",
        "project_name",
        "status",
        "phase",
        "due_date",
        "completion_pct",
        "is_critical_path",
        "created_at",
    )
    list_filter = (
        "status",
        "phase",
        "is_critical_path",
        "created_at",
    )
    search_fields = ("name", "description", "project__name")
    ordering = ("-due_date",)
    readonly_fields = ("id", "completion_pct", "created_at", "updated_at")
    list_select_related = ("project",)
    date_hierarchy = "due_date"

    @admin.display(description="Project")
    def project_name(self, obj: ProjectMilestone) -> str:
        return obj.project.name if obj.project else "—"


@admin.register(CommunicationLog)
class CommunicationLogAdmin(admin.ModelAdmin):
    """Admin for CommunicationLog model."""

    list_display = (
        "client_name",
        "contact_name",
        "channel",
        "direction",
        "subject",
        "sentiment",
        "is_flagged",
        "is_billable",
        "duration_minutes",
        "created_at",
    )
    list_filter = (
        "channel",
        "direction",
        "sentiment",
        "is_flagged",
        "is_billable",
        "created_at",
    )
    search_fields = (
        "subject",
        "body",
        "client__name",
        "contact__name",
    )
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")
    list_select_related = ("client", "contact")

    @admin.display(description="Client")
    def client_name(self, obj: CommunicationLog) -> str:
        return obj.client.name if obj.client else "—"

    @admin.display(description="Contact")
    def contact_name(self, obj: CommunicationLog) -> str:
        return obj.contact.name if obj.contact else "—"
