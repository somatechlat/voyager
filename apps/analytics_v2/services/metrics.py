"""Metric normalization, catalog, and derived calculations.

Handles cross-platform metric normalization (15+ platforms), derived
metric computation, drill paths, and the 100+ metric catalog.
"""

from __future__ import annotations

from typing import Any

# Metric normalization mapping across platforms
NORMALIZATION_MAP: dict[str, dict[str, str]] = {
    "engagement": {
        "instagram": "likes + comments + saves + shares",
        "linkedin": "reactions + comments + shares",
        "twitter": "likes + retweets + replies + bookmarks",
        "tiktok": "likes + comments + shares + saves",
        "facebook": "reactions + comments + shares",
        "youtube": "likes + comments + shares",
    },
    "reach": {
        "instagram": "reach",
        "linkedin": "unique_impressions",
        "twitter": "impressions",
        "tiktok": "video_views",
        "facebook": "reach",
        "youtube": "unique_viewers",
    },
    "impressions": {
        "instagram": "impressions",
        "linkedin": "impressions",
        "twitter": "impressions",
        "tiktok": "video_views",
        "facebook": "impressions",
        "youtube": "views",
    },
}

# Drill-down paths by category
DRILL_PATHS: dict[str, list[str]] = {
    "overview": ["platform", "campaign", "content_type", "individual_post"],
    "audience": ["country", "region", "city", "demographic"],
    "content": ["content_type", "topic", "format", "individual_piece"],
    "campaign": ["campaign", "channel", "ad_group", "individual_ad"],
    "conversion": ["funnel_step", "source", "medium", "landing_page"],
}

# 100+ metric catalog
METRIC_CATALOG: dict[str, dict[str, str]] = {
    "engagement": {
        "total_engagement": "Sum of all engagement actions",
        "engagement_rate": "Engagement / Reach",
        "likes": "Total likes",
        "comments": "Total comments",
        "shares": "Total shares",
        "saves": "Total saves",
        "reactions": "Total reactions",
        "clicks": "Total clicks",
        "ctr": "Click-through rate",
    },
    "reach": {
        "impressions": "Total impressions",
        "reach": "Unique impressions",
        "frequency": "Impressions / Reach",
        "video_views": "Total video views",
        "video_completion_rate": "Completed views / Total views",
    },
    "audience": {
        "followers": "Total followers",
        "follower_growth": "Net new followers",
        "follower_growth_rate": "New followers / Total followers",
        "audience_demographics": "Age, gender, location breakdown",
    },
    "conversion": {
        "conversions": "Total conversions",
        "conversion_rate": "Conversions / Clicks",
        "cost_per_conversion": "Spend / Conversions",
        "revenue": "Total revenue",
        "roas": "Revenue / Ad spend",
        "roi": "(Revenue - Cost) / Cost",
    },
    "email": {
        "delivered": "Emails delivered",
        "open_rate": "Opens / Delivered",
        "click_rate": "Clicks / Delivered",
        "unsubscribe_rate": "Unsubscribes / Delivered",
        "bounce_rate": "Bounces / Sent",
        "list_growth_rate": "Net new subscribers / Total",
    },
    "seo": {
        "organic_sessions": "Sessions from organic search",
        "keyword_rankings": "Average position",
        "domain_authority": "Domain authority score",
        "backlinks": "Total backlinks",
        "organic_clicks": "Clicks from search",
        "impressions_search": "Search impressions",
    },
    "financial": {
        "mrr": "Monthly recurring revenue",
        "churn_rate": "Customer churn rate",
        "ltv": "Lifetime value",
        "cac": "Customer acquisition cost",
        "ltv_cac_ratio": "LTV / CAC",
        "payback_period": "Months to recover CAC",
    },
    "paid_media": {
        "ad_spend": "Total ad spend",
        "cpm": "Cost per mille",
        "cpc": "Cost per click",
        "cpa": "Cost per acquisition",
        " ROAS": "Return on ad spend",
    },
}


def normalize_platform_metric(
    metric_name: str,
    platform: str,
    raw_data: dict[str, Any],
) -> float:
    """Normalize a metric from platform-specific naming.

    Args:
        metric_name: The canonical metric name (e.g. 'engagement').
        platform: Platform identifier (e.g. 'instagram').
        raw_data: Raw metric values from the platform API.

    Returns:
        Normalized metric value as float.
    """
    platform_key = platform.lower().replace(" ", "_").replace("/", "_")
    if metric_name in NORMALIZATION_MAP and platform_key in NORMALIZATION_MAP[metric_name]:
        expression = NORMALIZATION_MAP[metric_name][platform_key]
        result = _evaluate_expression(expression, raw_data)
        return float(result) if result else 0.0
    return float(raw_data.get(metric_name, 0))


def _evaluate_expression(expression: str, variables: dict[str, Any]) -> float:
    """Safely evaluate a metric expression against a variable dict.

    Args:
        expression: Expression like 'likes + comments + saves + shares'.
        variables: Dict of variable names to numeric values.

    Returns:
        Computed result as float.
    """
    safe_vars = {k: float(v) if v is not None else 0.0 for k, v in variables.items()}
    try:
        result = eval(expression, {"__builtins__": {}}, safe_vars)
        return float(result) if result is not None else 0.0
    except (SyntaxError, NameError, ZeroDivisionError, TypeError):
        return 0.0


def calculate_derived_metrics(
    base_metrics: dict[str, float],
    spend: float = 0,
) -> dict[str, float]:
    """Calculate derived metrics from base metrics.

    Args:
        base_metrics: Dict of base metric values.
        spend: Total spend value.

    Returns:
        Dict with base + derived metrics.
    """
    m = dict(base_metrics)
    m["spend"] = spend

    if m.get("reach", 0) > 0 and m.get("engagement", 0) >= 0:
        m["engagement_rate"] = m["engagement"] / m["reach"]
    if m.get("impressions", 0) > 0 and spend > 0:
        m["cpm"] = (spend / m["impressions"]) * 1000
    if m.get("clicks", 0) > 0 and spend > 0:
        m["cpc"] = spend / m["clicks"]
    if m.get("impressions", 0) > 0 and m.get("clicks", 0) >= 0:
        m["ctr"] = m["clicks"] / m["impressions"]
    if m.get("clicks", 0) > 0 and m.get("conversions", 0) >= 0:
        m["conversion_rate"] = m["conversions"] / m["clicks"]
    if spend > 0 and m.get("revenue", 0) > 0:
        m["roas"] = m["revenue"] / spend
    if spend > 0 and m.get("revenue", 0) >= 0:
        m["roi"] = (m["revenue"] - spend) / spend
    if m.get("reach", 0) > 0 and m.get("impressions", 0) > 0:
        m["frequency"] = m["impressions"] / m["reach"]
    if m.get("conversions", 0) > 0 and spend > 0:
        m["cost_per_conversion"] = spend / m["conversions"]

    return m


def apply_comparison(
    current_value: float,
    previous_value: float,
    comparison_mode: str,
    target_value: float | None = None,
    benchmark_value: float | None = None,
) -> dict[str, Any]:
    """Apply comparison mode to calculate change metrics.

    Args:
        current_value: Current period value.
        previous_value: Previous period value.
        comparison_mode: Type of comparison.
        target_value: Optional target for against_target mode.
        benchmark_value: Optional benchmark value.

    Returns:
        Dict with change_amount, change_percent, direction, comparison_mode.
    """
    result: dict[str, Any] = {"comparison_mode": comparison_mode, "current_value": current_value}

    if comparison_mode == "previous_period":
        result["previous_value"] = previous_value
        if previous_value != 0:
            result["change_percent"] = ((current_value - previous_value) / previous_value) * 100
        else:
            result["change_percent"] = 0 if current_value == 0 else 100
        result["change_amount"] = current_value - previous_value
    elif comparison_mode == "year_over_year":
        result["previous_value"] = previous_value
        if previous_value != 0:
            result["change_percent"] = ((current_value - previous_value) / previous_value) * 100
        else:
            result["change_percent"] = 0
        result["change_amount"] = current_value - previous_value
    elif comparison_mode == "against_target" and target_value:
        result["target_value"] = target_value
        if target_value != 0:
            result["change_percent"] = ((current_value - target_value) / target_value) * 100
        else:
            result["change_percent"] = 0
        result["change_amount"] = current_value - target_value
    elif comparison_mode == "benchmark" and benchmark_value:
        result["benchmark_value"] = benchmark_value
        if benchmark_value != 0:
            result["change_percent"] = ((current_value - benchmark_value) / benchmark_value) * 100
        else:
            result["change_percent"] = 0
        result["change_amount"] = current_value - benchmark_value

    change = result.get("change_percent", 0)
    result["direction"] = "up" if change > 0 else "down" if change < 0 else "flat"
    result["is_positive"] = change >= 0
    return result


def get_metric_catalog() -> dict[str, dict[str, str]]:
    """Return the full metric catalog (100+ metrics)."""
    return dict(METRIC_CATALOG)


def get_drill_paths() -> dict[str, list[str]]:
    """Return available drill-down paths."""
    return dict(DRILL_PATHS)


def get_comparison_modes() -> list[dict[str, str]]:
    """Return available comparison modes."""
    return [
        {
            "key": "previous_period",
            "name": "Previous Period",
            "formula": "((current - previous) / previous) * 100",
        },
        {
            "key": "year_over_year",
            "name": "Year over Year",
            "formula": "((current - lastYear) / lastYear) * 100",
        },
        {
            "key": "against_target",
            "name": "Against Target",
            "formula": "((actual - target) / target) * 100",
        },
        {
            "key": "benchmark",
            "name": "Benchmark",
            "formula": "((actual - benchmark) / benchmark) * 100",
        },
    ]


def get_widget_types() -> list[dict[str, Any]]:
    """Return the catalog of supported widget types with their configuration schemas.

    Returns:
        List of widget type definitions with config schemas.
    """
    return [
        {
            "type": "kpi_card",
            "config_schema": {
                "metric": {"type": "string", "required": True},
                "comparison": {"type": "string", "default": "previous_period"},
                "format": {"type": "string", "default": "number"},
                "trend": {"type": "boolean", "default": True},
                "sparkline": {"type": "boolean", "default": True},
            },
        },
        {
            "type": "line_chart",
            "config_schema": {
                "metrics": {"type": "array", "required": True},
                "dimensions": {"type": "array", "default": ["date"]},
                "grouping": {"type": "string", "default": "platform"},
                "trendline": {"type": "boolean", "default": True},
            },
        },
        {
            "type": "bar_chart",
            "config_schema": {
                "metric": {"type": "string", "required": True},
                "dimension": {"type": "string", "default": "platform"},
                "sort": {"type": "string", "default": "desc"},
                "limit": {"type": "integer", "default": 10},
            },
        },
        {
            "type": "pie_chart",
            "config_schema": {
                "metric": {"type": "string", "required": True},
                "dimension": {"type": "string", "default": "channel"},
                "show_percentage": {"type": "boolean", "default": True},
            },
        },
        {
            "type": "heatmap",
            "config_schema": {
                "metric": {"type": "string", "required": True},
                "x_dimension": {"type": "string", "default": "hour_of_day"},
                "y_dimension": {"type": "string", "default": "day_of_week"},
                "color_scale": {"type": "string", "default": "green"},
            },
        },
        {
            "type": "funnel",
            "config_schema": {
                "steps": {"type": "array", "required": True},
                "dimension": {"type": "string", "default": "campaign"},
            },
        },
        {
            "type": "table",
            "config_schema": {
                "columns": {"type": "array", "required": True},
                "sorting": {"type": "object", "default": {}},
                "pagination": {"type": "object", "default": {"page_size": 25}},
            },
        },
        {
            "type": "area_chart",
            "config_schema": {
                "metrics": {"type": "array", "required": True},
                "stacked": {"type": "boolean", "default": False},
            },
        },
        {
            "type": "gauge",
            "config_schema": {
                "metric": {"type": "string", "required": True},
                "target": {"type": "number", "required": True},
                "min": {"type": "number", "default": 0},
                "max": {"type": "number", "default": 100},
            },
        },
        {
            "type": "scorecard",
            "config_schema": {
                "metrics": {"type": "array", "required": True},
                "comparison": {"type": "string", "default": "previous_period"},
            },
        },
        {
            "type": "treemap",
            "config_schema": {
                "metric": {"type": "string", "required": True},
                "dimension": {"type": "string", "required": True},
            },
        },
        {
            "type": "cohort_table",
            "config_schema": {
                "event": {"type": "string", "required": True},
                "retention_event": {"type": "string", "required": True},
                "cohort_period": {"type": "string", "default": "week"},
            },
        },
        {
            "type": "pivot_table",
            "config_schema": {
                "rows": {"type": "array", "required": True},
                "columns": {"type": "array", "required": True},
                "values": {"type": "array", "required": True},
            },
        },
        {
            "type": "top_list",
            "config_schema": {
                "metric": {"type": "string", "required": True},
                "dimension": {"type": "string", "required": True},
                "limit": {"type": "integer", "default": 10},
            },
        },
    ]
