"""Competitor benchmarking service.

Handles competitor performance comparison, metric calculation,
and trend analysis against brand performance.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from django.db.models import Avg

from apps.social_media.models import CompetitorBenchmark

logger = logging.getLogger(__name__)


def create_benchmark(
    tenant_id: str,
    platform: str,
    competitor_name: str,
    competitor_handle: str,
    period: str,
    brand_metrics: dict[str, Any],
    competitor_metrics: dict[str, Any],
    period_start: date | None = None,
    period_end: date | None = None,
) -> dict[str, Any]:
    """Create a competitor benchmark record.

    :param tenant_id: Tenant scope.
    :param platform: Source platform.
    :param competitor_name: Competitor brand name.
    :param competitor_handle: Platform handle.
    :param period: Metric period — weekly, monthly, quarterly.
    :param brand_metrics: Dict with brand performance data.
    :param competitor_metrics: Dict with competitor performance data.
    :param period_start: Start date.
    :param period_end: End date.
    :returns: Benchmark result.
    """
    if period_end is None:
        period_end = date.today()
    if period_start is None:
        delta = {"weekly": 7, "monthly": 30, "quarterly": 90}
        period_start = period_end - timedelta(days=delta.get(period, 7))

    engagement_diff = None
    if competitor_metrics.get("avg_engagement_rate") and brand_metrics.get(
        "avg_engagement_rate"
    ):
        engagement_diff = round(
            competitor_metrics["avg_engagement_rate"]
            - brand_metrics["avg_engagement_rate"],
            4,
        )

    follower_diff = (
        competitor_metrics.get("follower_growth", 0)
        - brand_metrics.get("follower_growth", 0)
    )

    benchmark = CompetitorBenchmark.objects.create(
        tenant_id=tenant_id,
        platform=platform,
        competitor_name=competitor_name,
        competitor_handle=competitor_handle,
        metric_period=period,
        period_start=period_start,
        period_end=period_end,
        posts_count=competitor_metrics.get("posts_count", 0),
        avg_engagement_rate=competitor_metrics.get("avg_engagement_rate"),
        avg_likes=competitor_metrics.get("avg_likes", 0),
        avg_comments=competitor_metrics.get("avg_comments", 0),
        avg_shares=competitor_metrics.get("avg_shares", 0),
        total_followers=competitor_metrics.get("total_followers", 0),
        follower_growth=competitor_metrics.get("follower_growth", 0),
        top_post_url=competitor_metrics.get("top_post_url", ""),
        top_post_engagement=competitor_metrics.get("top_post_engagement", 0),
        brand_posts_count=brand_metrics.get("posts_count", 0),
        brand_avg_engagement=brand_metrics.get("avg_engagement_rate"),
        brand_total_followers=brand_metrics.get("total_followers", 0),
        brand_follower_growth=brand_metrics.get("follower_growth", 0),
        engagement_diff=engagement_diff,
        follower_diff=follower_diff,
        content_themes=competitor_metrics.get("content_themes", []),
    )

    return {
        "benchmark_id": str(benchmark.id),
        "competitor_name": competitor_name,
        "platform": platform,
        "period": period,
        "engagement_diff": engagement_diff,
        "follower_diff": follower_diff,
    }


def get_competitor_comparison(
    tenant_id: str,
    platform: str,
    period: str = "monthly",
) -> list[dict[str, Any]]:
    """Get all competitor benchmarks for a platform.

    :param tenant_id: Tenant scope.
    :param platform: Platform name.
    :param period: Metric period.
    :returns: List of comparison dicts.
    """
    benchmarks = CompetitorBenchmark.objects.filter(
        tenant_id=tenant_id, platform=platform, metric_period=period
    ).order_by("-period_end")

    return [
        {
            "id": str(b.id),
            "competitor_name": b.competitor_name,
            "competitor_handle": b.competitor_handle,
            "period_start": str(b.period_start),
            "period_end": str(b.period_end),
            "competitor": {
                "posts_count": b.posts_count,
                "avg_engagement_rate": float(b.avg_engagement_rate) if b.avg_engagement_rate else 0,
                "avg_likes": b.avg_likes,
                "avg_comments": b.avg_comments,
                "avg_shares": b.avg_shares,
                "total_followers": b.total_followers,
                "follower_growth": b.follower_growth,
            },
            "brand": {
                "posts_count": b.brand_posts_count,
                "avg_engagement_rate": float(b.brand_avg_engagement) if b.brand_avg_engagement else 0,
                "total_followers": b.brand_total_followers,
                "follower_growth": b.brand_follower_growth,
            },
            "diff": {
                "engagement_diff": float(b.engagement_diff) if b.engagement_diff else 0,
                "follower_diff": b.follower_diff,
            },
            "content_themes": b.content_themes,
        }
        for b in benchmarks
    ]


def get_leaderboard(
    tenant_id: str,
    platform: str,
    metric: str = "engagement",
    period: str = "monthly",
) -> list[dict[str, Any]]:
    """Get a ranked leaderboard of competitors by metric.

    :param tenant_id: Tenant scope.
    :param platform: Platform name.
    :param metric: Metric to rank by — engagement, followers, posts.
    :param period: Metric period.
    :returns: Ranked list of competitor dicts.
    """
    benchmarks = CompetitorBenchmark.objects.filter(
        tenant_id=tenant_id, platform=platform, metric_period=period
    ).order_by("-period_end")

    field_map = {
        "engagement": "avg_engagement_rate",
        "followers": "total_followers",
        "posts": "posts_count",
    }
    field = field_map.get(metric, "avg_engagement_rate")

    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for b in benchmarks:
        key = b.competitor_handle
        if key in seen:
            continue
        seen.add(key)
        value = getattr(b, field, 0)
        results.append(
            {
                "competitor_name": b.competitor_name,
                "competitor_handle": b.competitor_handle,
                "metric": metric,
                "value": float(value) if value else 0,
                "period_end": str(b.period_end),
            }
        )

    results.sort(key=lambda x: x["value"], reverse=True)
    for i, r in enumerate(results, 1):
        r["rank"] = i

    return results


def get_trend_analysis(
    tenant_id: str,
    competitor_handle: str,
    platform: str,
    metric: str = "avg_engagement_rate",
    periods: int = 6,
) -> list[dict[str, Any]]:
    """Get trend data for a competitor over multiple periods.

    :param tenant_id: Tenant scope.
    :param competitor_handle: Competitor handle.
    :param platform: Platform name.
    :param metric: Field to trend.
    :param periods: Number of periods.
    :returns: List of trend data points.
    """
    benchmarks = CompetitorBenchmark.objects.filter(
        tenant_id=tenant_id,
        competitor_handle=competitor_handle,
        platform=platform,
    ).order_by("-period_end")[:periods]

    return [
        {
            "period_start": str(b.period_start),
            "period_end": str(b.period_end),
            "competitor_value": float(getattr(b, metric, 0)) or 0,
            "brand_value": float(getattr(b, f"brand_{metric}", 0)) or 0,
            "diff": (
                float(getattr(b, metric, 0) or 0)
                - float(getattr(b, f"brand_{metric}", 0) or 0)
            ),
        }
        for b in reversed(list(benchmarks))
    ]


def aggregate_benchmarks(
    tenant_id: str,
    platform: str,
    period: str = "monthly",
) -> dict[str, Any]:
    """Get aggregated benchmark statistics.

    :param tenant_id: Tenant scope.
    :param platform: Platform name.
    :param period: Metric period.
    :returns: Aggregated stats.
    """
    qs = CompetitorBenchmark.objects.filter(
        tenant_id=tenant_id, platform=platform, metric_period=period
    )

    avg_engagement = qs.aggregate(avg=Avg("avg_engagement_rate")).get("avg") or 0
    brand_avg_engagement = qs.aggregate(avg=Avg("brand_avg_engagement")).get("avg") or 0

    return {
        "competitor_count": qs.count(),
        "avg_competitor_engagement": round(float(avg_engagement), 4),
        "avg_brand_engagement": round(float(brand_avg_engagement), 4),
        "platform": platform,
        "period": period,
    }
