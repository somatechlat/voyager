"""Django Admin for Billing app.

Registers TimeEntry, ProjectBudget, Invoice, Expense,
and Retainer models.
"""

from __future__ import annotations

import json

from django.contrib import admin

from apps.billing.models import (
    Expense,
    Invoice,
    LineItem,
    Payment,
    ProjectBudget,
    Retainer,
    TimeEntry,
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


class LineItemInline(admin.TabularInline):
    """Inline for LineItem within Invoice."""

    model = LineItem
    extra = 0
    readonly_fields = ("id", "created_at")


class PaymentInline(admin.TabularInline):
    """Inline for Payment within Invoice."""

    model = Payment
    extra = 0
    readonly_fields = ("id", "created_at")


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    """Admin for TimeEntry model."""

    list_display = (
        "user_id_short",
        "project_name",
        "task_description_preview",
        "duration_minutes",
        "hourly_rate",
        "total_cost",
        "is_billable",
        "is_billed",
        "date",
        "status",
        "created_at",
    )
    list_filter = (
        "is_billable",
        "is_billed",
        "status",
        "date",
        "created_at",
    )
    search_fields = (
        "task_description",
        "user_id",
        "project_id",
        "task_id",
        "tenant_id",
    )
    ordering = ("-date",)
    readonly_fields = ("id", "total_cost", "created_at", "updated_at")
    date_hierarchy = "date"

    @admin.display(description="User")
    def user_id_short(self, obj: TimeEntry) -> str:
        return obj.user_id[:12] + "..." if len(obj.user_id) > 12 else obj.user_id

    @admin.display(description="Project")
    def project_name(self, obj: TimeEntry) -> str:
        return obj.project_id[:12] + "..." if len(obj.project_id) > 12 else obj.project_id

    @admin.display(description="Task")
    def task_description_preview(self, obj: TimeEntry) -> str:
        return obj.task_description[:40] if obj.task_description else "—"


@admin.register(ProjectBudget)
class ProjectBudgetAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for ProjectBudget model."""

    list_display = (
        "project_id_short",
        "total_budget",
        "spent",
        "remaining",
        "forecasted_spend",
        "health_status",
        "variance_pct",
        "tenant_id_short",
        "created_at",
    )
    list_filter = (
        "health_status",
        "is_locked",
        "created_at",
    )
    search_fields = ("project_id", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "spent",
        "remaining",
        "forecasted_spend",
        "variance_pct",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Project")
    def project_id_short(self, obj: ProjectBudget) -> str:
        return obj.project_id[:12] + "..." if len(obj.project_id) > 12 else obj.project_id

    @admin.display(description="Categories")
    def display_categories(self, obj: ProjectBudget) -> str:
        return self._format_json(obj.category_breakdown_json, 200)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """Admin for Invoice model."""

    list_display = (
        "invoice_number",
        "client_name",
        "project_name",
        "status",
        "subtotal",
        "tax_total",
        "total",
        "amount_paid",
        "amount_due",
        "issue_date",
        "due_date",
        "paid_at",
        "overdue_days",
    )
    list_filter = (
        "status",
        "issue_date",
        "due_date",
        "created_at",
    )
    search_fields = (
        "invoice_number",
        "client_id",
        "project_id",
        "po_number",
        "notes",
    )
    ordering = ("-issue_date",)
    readonly_fields = (
        "id",
        "subtotal",
        "tax_total",
        "total",
        "amount_paid",
        "amount_due",
        "created_at",
        "updated_at",
    )
    inlines = [LineItemInline, PaymentInline]
    date_hierarchy = "issue_date"

    @admin.display(description="Client")
    def client_name(self, obj: Invoice) -> str:
        return obj.client_id[:12] + "..." if len(obj.client_id) > 12 else obj.client_id

    @admin.display(description="Project")
    def project_name(self, obj: Invoice) -> str:
        return obj.project_id[:12] + "..." if len(obj.project_id) > 12 else obj.project_id


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    """Admin for Expense model."""

    list_display = (
        "description_preview",
        "category",
        "amount",
        "currency",
        "vendor",
        "is_billable",
        "is_billed",
        "is_reimbursable",
        "expense_date",
        "status",
        "created_at",
    )
    list_filter = (
        "category",
        "is_billable",
        "is_billed",
        "is_reimbursable",
        "status",
        "expense_date",
        "created_at",
    )
    search_fields = (
        "description",
        "vendor",
        "receipt_url",
        "tenant_id",
    )
    ordering = ("-expense_date",)
    readonly_fields = ("id", "created_at", "updated_at")
    date_hierarchy = "expense_date"

    @admin.display(description="Description")
    def description_preview(self, obj: Expense) -> str:
        return obj.description[:40] if obj.description else "—"


@admin.register(Retainer)
class RetainerAdmin(admin.ModelAdmin):
    """Admin for Retainer model."""

    list_display = (
        "client_id_short",
        "name",
        "total_amount",
        "amount_used",
        "amount_remaining",
        "overage_amount",
        "hours_included",
        "hours_used",
        "status",
        "start_date",
        "end_date",
        "auto_renew",
    )
    list_filter = (
        "status",
        "auto_renew",
        "start_date",
        "end_date",
        "created_at",
    )
    search_fields = (
        "name",
        "client_id",
        "scope_of_work",
        "tenant_id",
    )
    ordering = ("-start_date",)
    readonly_fields = (
        "id",
        "amount_used",
        "amount_remaining",
        "overage_amount",
        "hours_used",
        "utilization_pct",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "start_date"

    @admin.display(description="Client")
    def client_id_short(self, obj: Retainer) -> str:
        return obj.client_id[:12] + "..." if len(obj.client_id) > 12 else obj.client_id
