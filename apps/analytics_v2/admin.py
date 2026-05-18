"""Django Admin for Analytics V2 app.

Registers Dashboard, Widget, ReportTemplate, AttributionModel,
and AnomalyDetection models.
"""

from __future__ import annotations

import json

from django.contrib import admin

from apps.analytics_v2.models import (
    AnomalyDetection,
    AttributionModel,
    Dashboard,
    DashboardShare,
    DashboardWidget,
    ReportSchedule,
    ReportTemplate,
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


class DashboardWidgetInline(admin.TabularInline):
    """Inline for DashboardWidget."""

    model = DashboardWidget
    extra = 0
    readonly_fields = ("id", "created_at")


class DashboardShareInline(admin.TabularInline):
    """Inline for DashboardShare."""

    model = DashboardShare
    extra = 0
    readonly_fields = ("id", "created_at")


class ReportScheduleInline(admin.TabularInline):
    """Inline for ReportSchedule."""

    model = ReportSchedule
    extra = 0
    readonly_fields = ("id", "created_at")


@admin.register(Dashboard)
class DashboardAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for Dashboard model."""

    list_display = (
        "name",
        "dashboard_type",
        "is_template",
        "is_favorite",
        "tenant_id_short",
        "created_at",
        "updated_at",
    )
    list_filter = ("dashboard_type", "is_template", "is_favorite", "created_at")
    search_fields = ("name", "description", "tenant_id")
    ordering = ("-updated_at",)
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [DashboardWidgetInline, DashboardShareInline]

    @admin.display(description="Layout")
    def display_layout(self, obj: Dashboard) -> str:
        return self._format_json(obj.layout_json, 200)

    @admin.display(description="Filters")
    def display_filters(self, obj: Dashboard) -> str:
        return self._format_json(obj.filters_json, 200)


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(_JSONMixin, admin.ModelAdmin):
    """Admin for DashboardWidget model."""

    list_display = (
        "name",
        "widget_type",
        "data_source",
        "chart_type",
        "created_at",
    )
    list_filter = ("widget_type", "chart_type", "data_source", "created_at")
    search_fields = ("name", "description")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")

    @admin.display(description="Config")
    def display_config(self, obj: DashboardWidget) -> str:
        return self._format_json(obj.config_json, 200)


@admin.register(ReportTemplate)
class ReportTemplateAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for ReportTemplate model."""

    list_display = (
        "name",
        "report_type",
        "output_format",
        "is_system",
        "tenant_id_short",
        "created_at",
    )
    list_filter = ("report_type", "output_format", "is_system", "created_at")
    search_fields = ("name", "description", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [ReportScheduleInline]

    @admin.display(description="Sections")
    def display_sections(self, obj: ReportTemplate) -> str:
        return self._format_json(obj.sections_json, 200)

    @admin.display(description="Config")
    def display_config(self, obj: ReportTemplate) -> str:
        return self._format_json(obj.config_json, 200)


@admin.register(AttributionModel)
class AttributionModelAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for AttributionModel model."""

    list_display = (
        "name",
        "model_type",
        "is_active",
        "date_range_days",
        "tenant_id_short",
        "created_at",
    )
    list_filter = ("model_type", "is_active", "created_at")
    search_fields = ("name", "description", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")

    @admin.display(description="Touchpoints")
    def display_touchpoints(self, obj: AttributionModel) -> str:
        return self._format_json(obj.touchpoint_weights_json, 200)

    @admin.display(description="Custom Weights")
    def display_weights(self, obj: AttributionModel) -> str:
        return self._format_json(obj.custom_weights_json, 200)

    @admin.display(description="Segments")
    def display_segments(self, obj: AttributionModel) -> str:
        return self._format_json(obj.segment_filters_json, 150)


@admin.register(AnomalyDetection)
class AnomalyDetectionAdmin(_TenantIdMixin, admin.ModelAdmin):
    """Admin for AnomalyDetection model."""

    list_display = (
        "metric_name",
        "metric_type",
        "status",
        "confidence_score",
        "detected_at",
        "tenant_id_short",
    )
    list_filter = ("metric_type", "status", "detected_at")
    search_fields = ("metric_name", "tenant_id")
    ordering = ("-detected_at",)
    readonly_fields = ("id", "detected_at", "created_at")
    date_hierarchy = "detected_at"

    @admin.display(description="Current")
    def current_value_display(self, obj: AnomalyDetection) -> str:
        return f"{obj.current_value}"

    @admin.display(description="Expected")
    def expected_value_display(self, obj: AnomalyDetection) -> str:
        return f"{obj.expected_value_min:.4f} - {obj.expected_value_max:.4f}"
