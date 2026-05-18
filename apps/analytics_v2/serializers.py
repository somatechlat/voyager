"""Django Ninja schemas for the Analytics v2 API.

Provides request and response schemas for dashboards, widgets, reports,
attribution models, anomaly detection, exports, and saved queries.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from ninja import Schema

# Dashboard schemas


class WidgetConfigIn(Schema):
    """Widget configuration embedded in dashboard create/update."""

    widget_type: str
    title: str
    subtitle: str = ""
    position: dict[str, int] = {}
    config: dict[str, Any] = {}
    refresh_interval: int = 0


class DashboardCreateIn(Schema):
    """Request body for creating a dashboard."""

    name: str
    description: str = ""
    layout: dict[str, Any] = {}
    filters: dict[str, Any] = {}
    is_default: bool = False
    is_shared: bool = False
    shared_with: list[str] = []


class DashboardUpdateIn(Schema):
    """Request body for updating a dashboard."""

    name: str | None = None
    description: str | None = None
    layout: dict[str, Any] | None = None
    filters: dict[str, Any] | None = None
    is_default: bool | None = None
    is_shared: bool | None = None
    shared_with: list[str] | None = None


class DashboardOut(Schema):
    """Response schema for a dashboard."""

    id: UUID
    tenant_id: str
    name: str
    description: str
    layout: dict[str, Any]
    filters: dict[str, Any]
    is_default: bool
    is_shared: bool
    shared_with: list[str]
    created_by: str
    created_at: datetime
    updated_at: datetime


# Widget schemas


class WidgetCreateIn(Schema):
    """Request body for creating a widget."""

    widget_type: str
    title: str
    subtitle: str = ""
    position: dict[str, int] = {}
    config: dict[str, Any] = {}
    refresh_interval: int = 0


class WidgetUpdateIn(Schema):
    """Request body for updating a widget."""

    widget_type: str | None = None
    title: str | None = None
    subtitle: str | None = None
    position: dict[str, int] | None = None
    config: dict[str, Any] | None = None
    refresh_interval: int | None = None


class WidgetOut(Schema):
    """Response schema for a widget."""

    id: UUID
    dashboard_id: UUID
    widget_type: str
    title: str
    subtitle: str
    position: dict[str, int]
    config: dict[str, Any]
    refresh_interval: int
    created_at: datetime
    updated_at: datetime


# Report schemas


class ReportTemplateCreateIn(Schema):
    """Request body for creating a report template."""

    name: str
    description: str = ""
    category: str = "general"
    config: dict[str, Any] = {}
    format: str = "pdf"
    is_favorite: bool = False


class ReportTemplateUpdateIn(Schema):
    """Request body for updating a report template."""

    name: str | None = None
    description: str | None = None
    category: str | None = None
    config: dict[str, Any] | None = None
    format: str | None = None
    is_favorite: bool | None = None


class ReportTemplateOut(Schema):
    """Response schema for a report template."""

    id: UUID
    tenant_id: str
    name: str
    description: str
    category: str
    config: dict[str, Any]
    format: str
    is_favorite: bool
    created_by: str
    created_at: datetime
    updated_at: datetime


class ReportScheduleCreateIn(Schema):
    """Request body for creating a report schedule."""

    template_id: UUID
    name: str
    frequency: str = "weekly"
    cron_expression: str = ""
    delivery: dict[str, Any] = {}
    timezone: str = "UTC"
    is_active: bool = True


class ReportScheduleOut(Schema):
    """Response schema for a report schedule."""

    id: UUID
    tenant_id: str
    template_id: UUID
    name: str
    frequency: str
    cron_expression: str
    next_run_at: datetime | None
    last_run_at: datetime | None
    last_run_status: str
    delivery: dict[str, Any]
    timezone: str
    is_active: bool
    created_by: str
    created_at: datetime


class ReportGenerateIn(Schema):
    """Request body for on-demand report generation."""

    template_id: UUID
    format: str = "pdf"
    date_range: dict[str, str] = {}
    filters: dict[str, Any] = {}
    delivery: dict[str, Any] = {}


class ReportGenerateOut(Schema):
    """Response schema for report generation."""

    job_id: UUID
    status: str
    format: str
    download_url: str | None = None
    message: str = ""


# Attribution schemas


class AttributionModelCreateIn(Schema):
    """Request body for creating an attribution model."""

    name: str
    model_type: str = "last_touch"
    config: dict[str, Any] = {}
    lookback_window_days: int = 30
    is_default: bool = False


class AttributionModelUpdateIn(Schema):
    """Request body for updating an attribution model."""

    name: str | None = None
    model_type: str | None = None
    config: dict[str, Any] | None = None
    lookback_window_days: int | None = None
    is_default: bool | None = None


class AttributionModelOut(Schema):
    """Response schema for an attribution model."""

    id: UUID
    tenant_id: str
    name: str
    model_type: str
    config: dict[str, Any]
    lookback_window_days: int
    is_default: bool
    created_by: str
    created_at: datetime
    updated_at: datetime


class AttributionCalculateIn(Schema):
    """Request body for running attribution calculation."""

    model_id: UUID
    conversion_paths: list[dict[str, Any]] = []
    date_range: dict[str, str] = {}


class AttributionResultOut(Schema):
    """Response schema for attribution calculation results."""

    model_id: UUID
    model_type: str
    total_conversions: int
    total_revenue: float
    channel_credits: dict[str, Any]
    touchpoint_credits: list[dict[str, Any]]


class TouchpointOut(Schema):
    """Response schema for a touchpoint."""

    id: UUID
    conversion_id: UUID
    sequence_order: int
    touchpoint_type: str
    channel: str
    platform: str
    campaign: str
    timestamp: datetime
    credit: float
    revenue_attributed: float


class ConversionPathOut(Schema):
    """Response schema for a conversion path."""

    id: UUID
    tenant_id: str
    conversion_id: str
    user_id: str
    conversion_value: float
    conversion_date: datetime
    currency: str
    channel: str
    campaign: str
    total_touchpoints: int
    time_to_conversion_hours: float
    touchpoints: list[TouchpointOut] = []


# Anomaly schemas


class AnomalyAlertCreateIn(Schema):
    """Request body for creating an anomaly alert."""

    name: str
    metric: str
    platform: str = ""
    method: str = "zscore"
    threshold: float = 3.0
    lookback_days: int = 30
    comparison_mode: str = "absolute"
    channels: list[dict[str, Any]] = []
    cooldown_minutes: int = 60
    enabled: bool = True


class AnomalyAlertUpdateIn(Schema):
    """Request body for updating an anomaly alert."""

    name: str | None = None
    metric: str | None = None
    platform: str | None = None
    method: str | None = None
    threshold: float | None = None
    lookback_days: int | None = None
    comparison_mode: str | None = None
    channels: list[dict[str, Any]] | None = None
    cooldown_minutes: int | None = None
    enabled: bool | None = None


class AnomalyAlertOut(Schema):
    """Response schema for an anomaly alert."""

    id: UUID
    tenant_id: str
    name: str
    metric: str
    platform: str
    method: str
    threshold: float
    lookback_days: int
    comparison_mode: str
    channels: list[dict[str, Any]]
    cooldown_minutes: int
    enabled: bool
    last_triggered_at: datetime | None
    trigger_count: int
    created_by: str
    created_at: datetime


class AnomalyDetectIn(Schema):
    """Request body for on-demand anomaly detection."""

    metric: str
    platform: str = ""
    method: str = "zscore"
    date_range: dict[str, str] = {}
    threshold: float = 3.0
    lookback_days: int = 30


class AnomalyEventOut(Schema):
    """Response schema for an anomaly event."""

    id: UUID
    alert_id: UUID | None
    tenant_id: str
    metric: str
    anomaly_type: str
    severity: str
    expected_value: float | None
    actual_value: float | None
    deviation: float | None
    z_score: float | None
    method: str
    context: dict[str, Any]
    detected_at: datetime
    acknowledged_at: datetime | None
    acknowledged_by: str
    resolved_at: datetime | None


class AnomalyDetectOut(Schema):
    """Response schema for anomaly detection results."""

    metric: str
    method: str
    total_data_points: int
    anomaly_rate: float
    anomalies: list[AnomalyEventOut]


# Export schemas


class ExportCreateIn(Schema):
    """Request body for creating an export job."""

    name: str
    description: str = ""
    query: dict[str, Any] = {}
    format: str = "csv"
    columns: list[str] = []


class ExportOut(Schema):
    """Response schema for an export job."""

    id: UUID
    tenant_id: str
    name: str
    description: str
    format: str
    row_count: int
    file_size_bytes: int
    file_path: str
    download_url: str
    status: str
    progress_percent: int
    error_message: str
    started_at: datetime | None
    completed_at: datetime | None
    created_by: str
    created_at: datetime


# Saved Query schemas


class SavedQueryCreateIn(Schema):
    """Request body for creating a saved query."""

    name: str
    description: str = ""
    sql: str = ""
    query_builder: dict[str, Any] = {}
    data_source: str = "clickhouse"
    is_public: bool = False


class SavedQueryUpdateIn(Schema):
    """Request body for updating a saved query."""

    name: str | None = None
    description: str | None = None
    sql: str | None = None
    query_builder: dict[str, Any] | None = None
    data_source: str | None = None
    is_public: bool | None = None


class SavedQueryOut(Schema):
    """Response schema for a saved query."""

    id: UUID
    tenant_id: str
    name: str
    description: str
    sql: str
    query_builder: dict[str, Any]
    data_source: str
    is_public: bool
    last_run_at: datetime | None
    last_run_rows: int
    last_run_duration_ms: int
    created_by: str
    created_at: datetime
    updated_at: datetime


class QueryExecuteIn(Schema):
    """Request body for executing a saved or ad-hoc query."""

    query_id: UUID | None = None
    sql: str = ""
    query_builder: dict[str, Any] = {}
    data_source: str = "clickhouse"
    limit: int = 1000


class QueryExecuteOut(Schema):
    """Response schema for query execution."""

    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    execution_time_ms: int
    data_source: str


# Dashboard data / widget data schemas


class WidgetDataIn(Schema):
    """Request body for fetching widget data."""

    widget_id: UUID
    date_range: dict[str, str] = {}
    filters: dict[str, Any] = {}
    comparison: str = "none"


class WidgetDataOut(Schema):
    """Response schema for widget data."""

    widget_id: UUID
    widget_type: str
    title: str
    data: dict[str, Any]
    comparison_data: dict[str, Any] | None = None
    generated_at: datetime


class DashboardDataOut(Schema):
    """Response schema for full dashboard data."""

    dashboard_id: UUID
    name: str
    widgets: list[WidgetDataOut]
    filters_applied: dict[str, Any]
    generated_at: datetime
