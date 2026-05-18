"""Django Admin for Workflows V2 app.

Registers Workflow, WorkflowNode, WorkflowEdge, and WorkflowExecution models.
"""

from __future__ import annotations

import json

from django.contrib import admin

from apps.workflows_v2.models import (
    Workflow,
    WorkflowEdge,
    WorkflowExecution,
    WorkflowNode,
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


class WorkflowNodeInline(admin.TabularInline):
    """Inline for WorkflowNode within Workflow."""

    model = WorkflowNode
    extra = 0
    fields = ("node_id", "node_type", "label", "position_x", "position_y")
    readonly_fields = ("node_id",)


class WorkflowEdgeInline(admin.TabularInline):
    """Inline for WorkflowEdge within Workflow."""

    model = WorkflowEdge
    extra = 0
    fields = ("edge_id", "source_node_id", "target_node_id", "condition")
    readonly_fields = ("edge_id",)


@admin.register(Workflow)
class WorkflowAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for Workflow model."""

    list_display = (
        "name",
        "status",
        "version",
        "execution_count",
        "avg_duration_ms",
        "created_by_short",
        "is_template",
        "tenant_id_short",
        "created_at",
    )
    list_filter = (
        "status",
        "is_template",
        "is_system",
        "created_at",
    )
    search_fields = (
        "name",
        "description",
        "created_by",
        "tenant_id",
    )
    ordering = ("-updated_at",)
    readonly_fields = (
        "id",
        "execution_count",
        "success_count",
        "failure_count",
        "avg_duration_ms",
        "created_at",
        "updated_at",
    )
    inlines = [WorkflowNodeInline, WorkflowEdgeInline]

    @admin.display(description="Created By")
    def created_by_short(self, obj: Workflow) -> str:
        return obj.created_by[:12] + "..." if len(obj.created_by) > 12 else obj.created_by

    @admin.display(description="Variables")
    def display_variables(self, obj: Workflow) -> str:
        return self._format_json(obj.variables_json, 200)

    @admin.display(description="Triggers")
    def display_triggers(self, obj: Workflow) -> str:
        return self._format_json(obj.trigger_config_json, 200)

    @admin.display(description="Settings")
    def display_settings(self, obj: Workflow) -> str:
        return self._format_json(obj.settings_json, 150)


@admin.register(WorkflowNode)
class WorkflowNodeAdmin(_JSONMixin, admin.ModelAdmin):
    """Admin for WorkflowNode model."""

    list_display = (
        "workflow_name",
        "node_id",
        "node_type",
        "label",
        "status",
        "is_start",
        "is_end",
        "retries",
        "timeout_seconds",
        "created_at",
    )
    list_filter = (
        "node_type",
        "status",
        "is_start",
        "is_end",
        "created_at",
    )
    search_fields = (
        "label",
        "node_id",
        "workflow__name",
    )
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")
    list_select_related = ("workflow",)

    @admin.display(description="Workflow")
    def workflow_name(self, obj: WorkflowNode) -> str:
        return obj.workflow.name if obj.workflow else "—"

    @admin.display(description="Config")
    def display_config(self, obj: WorkflowNode) -> str:
        return self._format_json(obj.config_json, 200)

    @admin.display(description="AI Prompt")
    def display_ai_prompt(self, obj: WorkflowNode) -> str:
        if not obj.ai_prompt:
            return "—"
        return obj.ai_prompt[:100] + "..." if len(obj.ai_prompt) > 100 else obj.ai_prompt


@admin.register(WorkflowEdge)
class WorkflowEdgeAdmin(admin.ModelAdmin):
    """Admin for WorkflowEdge model."""

    list_display = (
        "workflow_name",
        "edge_id",
        "source_node_id",
        "target_node_id",
        "edge_type",
        "is_default",
        "created_at",
    )
    list_filter = (
        "edge_type",
        "is_default",
        "created_at",
    )
    search_fields = (
        "edge_id",
        "source_node_id",
        "target_node_id",
        "workflow__name",
    )
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")
    list_select_related = ("workflow",)

    @admin.display(description="Workflow")
    def workflow_name(self, obj: WorkflowEdge) -> str:
        return obj.workflow.name if obj.workflow else "—"

    @admin.display(description="Condition")
    def display_condition(self, obj: WorkflowEdge) -> str:
        if not obj.condition:
            return "—"
        return obj.condition[:100] + "..." if len(obj.condition) > 100 else obj.condition


@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(_JSONMixin, admin.ModelAdmin):
    """Admin for WorkflowExecution model."""

    list_display = (
        "workflow_name",
        "status",
        "execution_mode",
        "started_at",
        "completed_at",
        "duration_ms",
        "success_rate",
        "error_count",
        "retries_used",
        "triggered_by_short",
        "created_at",
    )
    list_filter = (
        "status",
        "execution_mode",
        "started_at",
        "created_at",
    )
    search_fields = (
        "workflow__name",
        "triggered_by",
        "tenant_id",
    )
    ordering = ("-started_at",)
    readonly_fields = (
        "id",
        "started_at",
        "completed_at",
        "duration_ms",
        "success_rate",
        "error_count",
        "retries_used",
        "created_at",
    )
    date_hierarchy = "started_at"
    list_select_related = ("workflow",)

    @admin.display(description="Workflow")
    def workflow_name(self, obj: WorkflowExecution) -> str:
        return obj.workflow.name if obj.workflow else "—"

    @admin.display(description="Triggered By")
    def triggered_by_short(self, obj: WorkflowExecution) -> str:
        return obj.triggered_by[:12] + "..." if len(obj.triggered_by) > 12 else obj.triggered_by

    @admin.display(description="Success Rate")
    def success_rate(self, obj: WorkflowExecution) -> str:
        return f"{obj.success_rate:.1f}%"

    @admin.display(description="Output")
    def display_output(self, obj: WorkflowExecution) -> str:
        return self._format_json(obj.output_json, 200)

    @admin.display(description="Context")
    def display_context(self, obj: WorkflowExecution) -> str:
        return self._format_json(obj.context_json, 200)
