"""Competitor benchmarking views.

Endpoints for competitor comparison, leaderboards, trend analysis,
and benchmark creation.
"""

from __future__ import annotations

from datetime import date

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.social_media.services.benchmarking import (
    aggregate_benchmarks,
    create_benchmark,
    get_competitor_comparison,
    get_leaderboard,
    get_trend_analysis,
)

router = Router(auth=VoyagerKeycloakBearer())


class BenchmarkIn:
    """Input schema for creating a benchmark."""

    platform: str
    competitor_name: str
    competitor_handle: str
    period: str = "monthly"
    brand_posts_count: int = 0
    brand_avg_engagement_rate: float = 0
    brand_total_followers: int = 0
    brand_follower_growth: int = 0
    competitor_posts_count: int = 0
    competitor_avg_engagement_rate: float = 0
    competitor_total_followers: int = 0
    competitor_follower_growth: int = 0
    competitor_avg_likes: int = 0
    competitor_avg_comments: int = 0
    competitor_avg_shares: int = 0
    competitor_top_post_url: str = ""
    competitor_top_post_engagement: int = 0
    competitor_content_themes: list[str] = []
    period_start: str = ""
    period_end: str = ""


class BenchmarkOut:
    """Output schema for a benchmark result."""

    benchmark_id: str
    competitor_name: str
    platform: str
    period: str
    engagement_diff: float
    follower_diff: int


@router.get("/comparison", response=list[dict], tags=["SM Benchmarking"])
def comparison(
    request,
    tenant_id: str = "",
    platform: str = "",
    period: str = "monthly",
):
    """Get competitor comparison data."""
    return get_competitor_comparison(
        tenant_id=tenant_id,
        platform=platform,
        period=period,
    )


@router.post("/benchmarks", response=BenchmarkOut, tags=["SM Benchmarking"])
def create_benchmark_view(request, payload: BenchmarkIn):
    """Create a competitor benchmark."""
    tenant_id = getattr(request, "tenant_id", "default")
    brand_metrics = {
        "posts_count": payload.brand_posts_count,
        "avg_engagement_rate": payload.brand_avg_engagement_rate,
        "total_followers": payload.brand_total_followers,
        "follower_growth": payload.brand_follower_growth,
    }
    competitor_metrics = {
        "posts_count": payload.competitor_posts_count,
        "avg_engagement_rate": payload.competitor_avg_engagement_rate,
        "total_followers": payload.competitor_total_followers,
        "follower_growth": payload.competitor_follower_growth,
        "avg_likes": payload.competitor_avg_likes,
        "avg_comments": payload.competitor_avg_comments,
        "avg_shares": payload.competitor_avg_shares,
        "top_post_url": payload.competitor_top_post_url,
        "top_post_engagement": payload.competitor_top_post_engagement,
        "content_themes": payload.competitor_content_themes,
    }
    result = create_benchmark(
        tenant_id=tenant_id,
        platform=payload.platform,
        competitor_name=payload.competitor_name,
        competitor_handle=payload.competitor_handle,
        period=payload.period,
        brand_metrics=brand_metrics,
        competitor_metrics=competitor_metrics,
        period_start=_parse_date(payload.period_start) if payload.period_start else None,
        period_end=_parse_date(payload.period_end) if payload.period_end else None,
    )
    return BenchmarkOut(**result)


@router.get("/leaderboard", response=list[dict], tags=["SM Benchmarking"])
def leaderboard(
    request,
    tenant_id: str = "",
    platform: str = "",
    metric: str = "engagement",
    period: str = "monthly",
):
    """Get competitor leaderboard."""
    return get_leaderboard(
        tenant_id=tenant_id,
        platform=platform,
        metric=metric,
        period=period,
    )


@router.get("/trends", response=list[dict], tags=["SM Benchmarking"])
def trends(
    request,
    tenant_id: str = "",
    competitor_handle: str = "",
    platform: str = "",
    metric: str = "avg_engagement_rate",
    periods: int = 6,
):
    """Get trend analysis for a competitor."""
    return get_trend_analysis(
        tenant_id=tenant_id,
        competitor_handle=competitor_handle,
        platform=platform,
        metric=metric,
        periods=periods,
    )


@router.get("/aggregate", response=dict, tags=["SM Benchmarking"])
def aggregate(request, tenant_id: str = "", platform: str = "", period: str = "monthly"):
    """Get aggregated benchmark statistics."""
    return aggregate_benchmarks(
        tenant_id=tenant_id,
        platform=platform,
        period=period,
    )


@router.get("/benchmarks/stats/overview", response=dict, tags=["SM Benchmarking"])
def benchmark_stats(request, tenant_id: str = ""):
    """Get benchmark overview statistics."""
    from apps.social_media.models import CompetitorBenchmark

    qs = CompetitorBenchmark.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    return {
        "total_benchmarks": qs.count(),
        "competitors_tracked": qs.values("competitor_handle").distinct().count(),
        "platforms": list(qs.values_list("platform", flat=True).distinct()),
        "latest_period": (qs.order_by("-period_end").values_list("period_end", flat=True).first()),
    }


def _parse_date(value: str) -> date:
    """Parse date string."""
    return date.fromisoformat(value)
