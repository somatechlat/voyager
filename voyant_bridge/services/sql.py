"""VoyantSQLService — SQL execution via Voyant/Trino."""

from __future__ import annotations

import logging
from typing import Any

from voyant_bridge.client import voyant_client

logger = logging.getLogger(__name__)


class VoyantSQLService:
    """Service for SQL execution via Voyant/Trino.

    Wraps ``/api/v1/sql/query`` with pre-built query templates
    for common Voyager use cases.
    """

    CATALOG: str = "iceberg"

    async def query_campaign_performance(
        self,
        campaign_id: str,
        tenant_id: str,
        token: str,
        date_range: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Query campaign performance from ClickHouse via Trino.

        Used by: ``campaigns`` (performance dashboards).

        :param campaign_id: Campaign identifier.
        :param tenant_id: Tenant identifier.
        :param token: Bearer JWT token.
        :param date_range: Optional dict with ``start`` and ``end`` dates.
        :returns: SQL result dict with ``columns``, ``rows``, ``row_count``.
        """
        date_filter = ""
        if date_range:
            date_filter = (
                f" AND event_date >= DATE '{date_range['start']}'"
                f" AND event_date <= DATE '{date_range['end']}'"
            )

        query = (
            f"SELECT "
            f"  campaign_id, event_date, "
            f"  SUM(impressions) AS impressions, "
            f"  SUM(clicks) AS clicks, "
            f"  SUM(conversions) AS conversions, "
            f"  SUM(spend) AS spend, "
            f"  ROUND(SUM(clicks) * 1.0 / NULLIF(SUM(impressions), 0), 4) AS ctr, "
            f"  ROUND(SUM(conversions) * 1.0 / NULLIF(SUM(clicks), 0), 4) AS cvr, "
            f"  ROUND(SUM(spend) * 1.0 / NULLIF(SUM(conversions), 0), 2) AS cpa "
            f"FROM {self.CATALOG}.{tenant_id}.campaign_events "
            f"WHERE campaign_id = '{campaign_id}'{date_filter} "
            f"GROUP BY campaign_id, event_date "
            f"ORDER BY event_date DESC"
        )
        result = await voyant_client.execute_sql(query, self.CATALOG, token)
        logger.info(
            "Campaign performance queried: %s, %d rows",
            campaign_id,
            result.get("row_count", 0),
        )
        return result

    async def query_dashboard_metrics(
        self,
        dashboard_config: dict[str, Any],
        tenant_id: str,
        token: str,
    ) -> dict[str, Any]:
        """Execute dashboard widget queries.

        Used by: ``analytics_v2.services.dashboard``.

        :param dashboard_config: Dict with ``widget_type`` and ``filters``.
            Supported types: ``"kpi_summary"``, ``"trend"``, ``"funnel"``,
            ``"breakdown"``.
        :param tenant_id: Tenant identifier.
        :param token: Bearer JWT token.
        :returns: SQL result dict with ``columns``, ``rows``, ``row_count``.
        """
        widget_type: str = dashboard_config.get("widget_type", "kpi_summary")
        filters: dict[str, Any] = dashboard_config.get("filters", {})
        schema = tenant_id

        if widget_type == "kpi_summary":
            query = (
                f"SELECT "
                f"  SUM(impressions) AS total_impressions, "
                f"  SUM(clicks) AS total_clicks, "
                f"  SUM(conversions) AS total_conversions, "
                f"  SUM(spend) AS total_spend, "
                f"  ROUND(SUM(clicks) * 1.0 / NULLIF(SUM(impressions), 0), 4) AS avg_ctr "
                f"FROM {self.CATALOG}.{schema}.campaign_events WHERE 1=1"
            )
        elif widget_type == "trend":
            date_col = filters.get("date_column", "event_date")
            query = (
                f"SELECT {date_col}, "
                f"  SUM(impressions) AS impressions, "
                f"  SUM(clicks) AS clicks, "
                f"  SUM(conversions) AS conversions "
                f"FROM {self.CATALOG}.{schema}.campaign_events WHERE 1=1 "
                f"GROUP BY {date_col} ORDER BY {date_col} DESC LIMIT 30"
            )
        elif widget_type == "funnel":
            query = (
                f"SELECT funnel_stage, "
                f"  COUNT(DISTINCT user_id) AS users, "
                f"  ROUND(COUNT(DISTINCT user_id) * 100.0 / "
                f"    SUM(COUNT(DISTINCT user_id)) OVER (), 2) AS pct "
                f"FROM {self.CATALOG}.{schema}.funnel_events WHERE 1=1 "
                f"GROUP BY funnel_stage ORDER BY users DESC"
            )
        elif widget_type == "breakdown":
            dimension: str = filters.get("dimension", "campaign_id")
            query = (
                f"SELECT {dimension}, "
                f"  SUM(impressions) AS impressions, "
                f"  SUM(clicks) AS clicks, "
                f"  SUM(conversions) AS conversions, "
                f"  SUM(spend) AS spend "
                f"FROM {self.CATALOG}.{schema}.campaign_events WHERE 1=1 "
                f"GROUP BY {dimension} ORDER BY spend DESC LIMIT 20"
            )
        else:
            raise ValueError(f"Unknown widget_type: {widget_type}")

        date_range = filters.get("date_range")
        if date_range:
            date_col = filters.get("date_column", "event_date")
            query = query.replace(
                "WHERE 1=1",
                f"WHERE {date_col} >= DATE '{date_range['start']}'"
                f" AND {date_col} <= DATE '{date_range['end']}'",
            )

        result = await voyant_client.execute_sql(query, self.CATALOG, token)
        logger.info(
            "Dashboard metrics queried: widget=%s schema=%s rows=%d",
            widget_type,
            schema,
            result.get("row_count", 0),
        )
        return result

    async def execute_custom_query(
        self,
        query: str,
        tenant_id: str,
        token: str,
        limit: int = 1000,
    ) -> dict[str, Any]:
        """Execute an arbitrary SQL query via Trino.

        :param query: SQL SELECT statement.
        :param tenant_id: Tenant identifier (used as schema).
        :param token: Bearer JWT token.
        :param limit: Maximum rows to return (default: 1000).
        :returns: SQL result dict with ``columns``, ``rows``, ``row_count``.
        """
        return await voyant_client.execute_sql(query, self.CATALOG, token, limit=limit)

    async def list_available_tables(
        self,
        tenant_id: str,
        token: str,
    ) -> list[str]:
        """List tables available to a tenant.

        :param tenant_id: Tenant identifier.
        :param token: Bearer JWT token.
        :returns: List of table name strings.
        """
        result = await voyant_client.list_tables(self.CATALOG, token, schema=tenant_id)
        return result.get("tables", [])
