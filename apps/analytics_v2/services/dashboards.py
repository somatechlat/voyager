"""Dashboard widget engine — renders widget data from analytics queries.

Fetches normalized metrics from ClickHouse, applies filters, comparisons,
and formats data for each widget type (KPI cards, charts, tables, funnels).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from apps.analytics_v2.services.fetchers import (
    fetch_metric_aggregate,
    fetch_metric_by_dimension,
    fetch_metric_heatmap,
    fetch_metric_series,
    fetch_metric_table,
)
from apps.analytics_v2.services.metrics import apply_comparison, normalize_platform_metric

logger = logging.getLogger(__name__)


def compute_date_range(
    preset: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> tuple[datetime, datetime]:
    """Compute date range from preset or explicit dates.

    Args:
        preset: Preset name (today, yesterday, last_7_days, last_30_days, etc.).
        start: Explicit start date ISO string.
        end: Explicit end date ISO string.

    Returns:
        Tuple of (start_dt, end_dt).
    """
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if start and end:
        return datetime.fromisoformat(start), datetime.fromisoformat(end)

    presets: dict[str, tuple[datetime, datetime]] = {
        "today": (today, now),
        "yesterday": (today - timedelta(days=1), today),
        "last_7_days": (today - timedelta(days=7), now),
        "last_14_days": (today - timedelta(days=14), now),
        "last_30_days": (today - timedelta(days=30), now),
        "last_90_days": (today - timedelta(days=90), now),
        "this_month": (today.replace(day=1), now),
        "last_month": (
            (today.replace(day=1) - timedelta(days=1)).replace(day=1),
            today.replace(day=1),
        ),
        "this_quarter": (
            today.replace(month=((today.month - 1) // 3) * 3 + 1, day=1),
            now,
        ),
        "this_year": (today.replace(month=1, day=1), now),
    }

    return presets.get(preset or "last_30_days", presets["last_30_days"])


def render_widget_data(
    widget_type: str,
    config: dict[str, Any],
    date_range: dict[str, str],
    filters: dict[str, Any],
    tenant_id: str,
) -> dict[str, Any]:
    """Render widget data by type — fetches and formats metrics.

    Args:
        widget_type: Widget type identifier.
        config: Widget configuration.
        date_range: Date range dict with start/end.
        filters: Applied filters.
        tenant_id: Tenant scope.

    Returns:
        Formatted widget data payload.
    """
    start_dt, end_dt = compute_date_range(
        date_range.get("preset"),
        date_range.get("start"),
        date_range.get("end"),
    )

    if widget_type == "kpi_card":
        return _render_kpi_card(config, start_dt, end_dt, filters, tenant_id)
    elif widget_type in ("line_chart", "area_chart"):
        return _render_line_chart(config, start_dt, end_dt, filters, tenant_id)
    elif widget_type == "bar_chart":
        return _render_bar_chart(config, start_dt, end_dt, filters, tenant_id)
    elif widget_type == "pie_chart":
        return _render_pie_chart(config, start_dt, end_dt, filters, tenant_id)
    elif widget_type == "table":
        return _render_table(config, start_dt, end_dt, filters, tenant_id)
    elif widget_type == "heatmap":
        return _render_heatmap(config, start_dt, end_dt, filters, tenant_id)
    elif widget_type == "funnel":
        return _render_funnel(config, start_dt, end_dt, filters, tenant_id)
    elif widget_type == "gauge":
        return _render_gauge(config, start_dt, end_dt, filters, tenant_id)
    elif widget_type == "scorecard":
        return _render_scorecard(config, start_dt, end_dt, filters, tenant_id)
    elif widget_type == "scatter_plot":
        return _render_scatter_plot(config, start_dt, end_dt, filters, tenant_id)
    elif widget_type == "treemap":
        return _render_treemap(config, start_dt, end_dt, filters, tenant_id)
    elif widget_type in ("cohort_table", "pivot_table"):
        return {"widget_type": widget_type, "data": {}, "note": "Use specialized renderer"}
    else:
        return {"widget_type": widget_type, "data": {}, "error": "Unsupported widget type"}


def _render_kpi_card(config, start_dt, end_dt, filters, tenant_id):
    metric = config.get("metric", "total_reach")
    comparison = config.get("comparison", "previous_period")
    fmt = config.get("format", "number")

    current = fetch_metric_aggregate(metric, start_dt, end_dt, filters, tenant_id)
    prev_start = start_dt - (end_dt - start_dt)
    previous = fetch_metric_aggregate(metric, prev_start, start_dt, filters, tenant_id)
    comparison_data = apply_comparison(current, previous, comparison)

    return {
        "widget_type": "kpi_card",
        "metric": metric,
        "value": current,
        "format": fmt,
        "comparison": comparison_data,
        "sparkline": fetch_metric_series(metric, start_dt, end_dt, filters, tenant_id, "day")
        if config.get("sparkline")
        else None,
    }


def _render_line_chart(config, start_dt, end_dt, filters, tenant_id):
    metrics = config.get("metrics", ["impressions"])
    grouping = config.get("grouping", "platform")
    series_data = {}
    for metric in metrics:
        series_data[metric] = fetch_metric_series(metric, start_dt, end_dt, filters, tenant_id, "day")
    return {
        "widget_type": "line_chart",
        "metrics": metrics,
        "grouping": grouping,
        "series": series_data,
        "dimensions": ["date"],
    }


def _render_bar_chart(config, start_dt, end_dt, filters, tenant_id):
    metric = config.get("metric", "engagement_rate")
    dimension = config.get("dimension", "platform")
    sort = config.get("sort", "desc")
    limit = config.get("limit", 10)
    data = fetch_metric_by_dimension(metric, dimension, start_dt, end_dt, filters, tenant_id)
    data = sorted(data, key=lambda x: x["value"], reverse=(sort == "desc"))[:limit]
    return {"widget_type": "bar_chart", "metric": metric, "dimension": dimension, "data": data}


def _render_pie_chart(config, start_dt, end_dt, filters, tenant_id):
    metric = config.get("metric", "spend")
    dimension = config.get("dimension", "channel")
    data = fetch_metric_by_dimension(metric, dimension, start_dt, end_dt, filters, tenant_id)
    total = sum(d["value"] for d in data) if data else 1
    if config.get("show_percentage", True):
        for d in data:
            d["percentage"] = (d["value"] / total) * 100
    return {"widget_type": "pie_chart", "metric": metric, "dimension": dimension, "data": data, "total": total}


def _render_table(config, start_dt, end_dt, filters, tenant_id):
    columns = config.get("columns", ["platform", "impressions", "engagement"])
    page_size = config.get("pagination", {}).get("page_size", 25)
    data = fetch_metric_table(columns, start_dt, end_dt, filters, tenant_id, page_size)
    return {
        "widget_type": "table",
        "columns": columns,
        "rows": data,
        "pagination": {"page_size": page_size, "total_rows": len(data)},
    }


def _render_heatmap(config, start_dt, end_dt, filters, tenant_id):
    metric = config.get("metric", "engagement_rate")
    x_dim = config.get("x_dimension", "hour_of_day")
    y_dim = config.get("y_dimension", "day_of_week")
    data = fetch_metric_heatmap(metric, x_dim, y_dim, start_dt, end_dt, filters, tenant_id)
    return {
        "widget_type": "heatmap",
        "metric": metric,
        "x_dimension": x_dim,
        "y_dimension": y_dim,
        "data": data,
        "color_scale": config.get("color_scale", "green"),
    }


def _render_funnel(config, start_dt, end_dt, filters, tenant_id):
    steps = config.get("steps", ["impressions", "clicks", "leads", "conversions"])
    dimension = config.get("dimension", "campaign")
    data = []
    for step in steps:
        value = fetch_metric_aggregate(step, start_dt, end_dt, filters, tenant_id)
        data.append({"step": step, "value": value})
    for i in range(1, len(data)):
        prev_val = data[i - 1]["value"]
        curr_val = data[i]["value"]
        data[i]["conversion_rate"] = (curr_val / prev_val * 100) if prev_val > 0 else 0
    return {"widget_type": "funnel", "dimension": dimension, "steps": data}


def _render_gauge(config, start_dt, end_dt, filters, tenant_id):
    metric = config.get("metric", "engagement_rate")
    target = config.get("target", 100)
    min_val = config.get("min", 0)
    max_val = config.get("max", 100)
    value = fetch_metric_aggregate(metric, start_dt, end_dt, filters, tenant_id)
    pct = ((value - min_val) / (max_val - min_val) * 100) if max_val > min_val else 0
    return {
        "widget_type": "gauge",
        "metric": metric,
        "value": value,
        "target": target,
        "min": min_val,
        "max": max_val,
        "percentage": pct,
    }


def _render_scorecard(config, start_dt, end_dt, filters, tenant_id):
    metrics = config.get("metrics", ["impressions", "clicks", "conversions"])
    comparison = config.get("comparison", "previous_period")
    prev_start = start_dt - (end_dt - start_dt)
    cards = []
    for metric in metrics:
        current = fetch_metric_aggregate(metric, start_dt, end_dt, filters, tenant_id)
        previous = fetch_metric_aggregate(metric, prev_start, start_dt, filters, tenant_id)
        comp = apply_comparison(current, previous, comparison)
        cards.append({"metric": metric, "value": current, "comparison": comp})
    return {"widget_type": "scorecard", "cards": cards}


def _render_scatter_plot(config, start_dt, end_dt, filters, tenant_id):
    x_metric = config.get("x_metric", "impressions")
    y_metric = config.get("y_metric", "engagement")
    x_data = fetch_metric_series(x_metric, start_dt, end_dt, filters, tenant_id, "day")
    y_data = fetch_metric_series(y_metric, start_dt, end_dt, filters, tenant_id, "day")
    return {
        "widget_type": "scatter_plot",
        "x_metric": x_metric,
        "y_metric": y_metric,
        "x_series": x_data,
        "y_series": y_data,
    }


def _render_treemap(config, start_dt, end_dt, filters, tenant_id):
    metric = config.get("metric", "spend")
    dimension = config.get("dimension", "channel")
    data = fetch_metric_by_dimension(metric, dimension, start_dt, end_dt, filters, tenant_id)
    return {"widget_type": "treemap", "metric": metric, "dimension": dimension, "data": data}
