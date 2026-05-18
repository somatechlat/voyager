"""ClickHouse data fetchers for widget rendering.

Provides chunked data retrieval for KPI cards, charts, tables, heatmaps,
and funnels from the analytics_events ClickHouse table.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def fetch_metric_aggregate(
    metric: str,
    start: datetime,
    end: datetime,
    filters: dict[str, Any],
    tenant_id: str,
) -> float:
    """Fetch aggregated metric value from ClickHouse.

    Args:
        metric: Metric name to aggregate.
        start: Start datetime.
        end: End datetime.
        filters: Query filters.
        tenant_id: Tenant scope.

    Returns:
        Aggregated float value.
    """
    try:
        from django.db import connections

        ch = connections.get("clickhouse")
        platform_filter = filters.get("platform", "")
        where = (
            f"tenant_id = '{tenant_id}' AND event_date BETWEEN '{start.date()}' AND '{end.date()}'"
        )
        if platform_filter:
            where += f" AND platform = '{platform_filter}'"

        sql = f"""
            SELECT sum(metric_value) as total
            FROM analytics_events
            WHERE {where}
            AND metric_name = '{metric}'
        """
        with ch.cursor() as cursor:
            cursor.execute(sql)
            row = cursor.fetchone()
            return float(row[0]) if row and row[0] else 0.0
    except Exception:
        return 0.0


def fetch_metric_series(
    metric: str,
    start: datetime,
    end: datetime,
    filters: dict[str, Any],
    tenant_id: str,
    granularity: str,
) -> list[dict[str, Any]]:
    """Fetch time-series metric data from ClickHouse."""
    try:
        from django.db import connections

        ch = connections.get("clickhouse")
        platform_filter = filters.get("platform", "")
        where = (
            f"tenant_id = '{tenant_id}' AND event_date BETWEEN '{start.date()}' AND '{end.date()}'"
        )
        if platform_filter:
            where += f" AND platform = '{platform_filter}'"

        group_by = "event_date"
        sql = f"""
            SELECT {group_by}, sum(metric_value) as total
            FROM analytics_events
            WHERE {where}
            AND metric_name = '{metric}'
            GROUP BY {group_by}
            ORDER BY {group_by}
        """
        with ch.cursor() as cursor:
            cursor.execute(sql)
            return [
                {"date": str(row[0]), "value": float(row[1]) if row[1] else 0.0}
                for row in cursor.fetchall()
            ]
    except Exception:
        return []


def fetch_metric_by_dimension(
    metric: str,
    dimension: str,
    start: datetime,
    end: datetime,
    filters: dict[str, Any],
    tenant_id: str,
) -> list[dict[str, Any]]:
    """Fetch metric aggregated by a dimension from ClickHouse."""
    try:
        from django.db import connections

        ch = connections.get("clickhouse")
        platform_filter = filters.get("platform", "")
        where = (
            f"tenant_id = '{tenant_id}' AND event_date BETWEEN '{start.date()}' AND '{end.date()}'"
        )
        if platform_filter:
            where += f" AND platform = '{platform_filter}'"

        dim_field = f"dimensions['{dimension}']"
        sql = f"""
            SELECT {dim_field} as dim, sum(metric_value) as total
            FROM analytics_events
            WHERE {where}
            AND metric_name = '{metric}'
            GROUP BY dim
            ORDER BY total DESC
        """
        with ch.cursor() as cursor:
            cursor.execute(sql)
            return [
                {"dimension": row[0] or "unknown", "value": float(row[1]) if row[1] else 0.0}
                for row in cursor.fetchall()
            ]
    except Exception:
        return []


def fetch_metric_table(
    columns: list[str],
    start: datetime,
    end: datetime,
    filters: dict[str, Any],
    tenant_id: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Fetch tabular metric data from ClickHouse."""
    try:
        from django.db import connections

        ch = connections.get("clickhouse")
        platform_filter = filters.get("platform", "")
        where = (
            f"tenant_id = '{tenant_id}' AND event_date BETWEEN '{start.date()}' AND '{end.date()}'"
        )
        if platform_filter:
            where += f" AND platform = '{platform_filter}'"

        metric_cols = ", ".join(
            f"sumIf(metric_value, metric_name = '{c}') as {c}" for c in columns if c != "platform"
        )
        sql = f"""
            SELECT platform, {metric_cols}
            FROM analytics_events
            WHERE {where}
            GROUP BY platform
            LIMIT {limit}
        """
        with ch.cursor() as cursor:
            cursor.execute(sql)
            cols = [desc[0] for desc in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
    except Exception:
        return []


def fetch_metric_heatmap(
    metric: str,
    x_dim: str,
    y_dim: str,
    start: datetime,
    end: datetime,
    filters: dict[str, Any],
    tenant_id: str,
) -> list[dict[str, Any]]:
    """Fetch heatmap data from ClickHouse."""
    try:
        from django.db import connections

        ch = connections.get("clickhouse")
        platform_filter = filters.get("platform", "")
        where = (
            f"tenant_id = '{tenant_id}' AND event_date BETWEEN '{start.date()}' AND '{end.date()}'"
        )
        if platform_filter:
            where += f" AND platform = '{platform_filter}'"

        x_field = f"dimensions['{x_dim}']"
        y_field = f"dimensions['{y_dim}']"
        sql = f"""
            SELECT {x_field} as x, {y_field} as y, avg(metric_value) as val
            FROM analytics_events
            WHERE {where}
            AND metric_name = '{metric}'
            GROUP BY x, y
        """
        with ch.cursor() as cursor:
            cursor.execute(sql)
            return [
                {"x": row[0], "y": row[1], "value": float(row[2]) if row[2] else 0.0}
                for row in cursor.fetchall()
            ]
    except Exception:
        return []
