"""Market Research service — SP-006 business logic.

Handles trend detection, market sizing, and competitive landscape
aggregation with lifecycle stage classification.
"""

from __future__ import annotations

import logging
import statistics
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from apps.strategy.models import CompetitorContent, CompetitorProfile, MarketResearch

logger = logging.getLogger(__name__)

# Lifecycle stage thresholds
EMERGING_THRESHOLD = 0.3
PEAKING_THRESHOLD = 0.1


class ResearchService:
    """Service for market research operations."""

    @staticmethod
    def create_research(
        tenant_id: str,
        industry: str,
        trends: list[dict[str, Any]] | None = None,
        market_size: dict[str, Any] | None = None,
        audience_insights: dict[str, Any] | None = None,
        competitive_landscape: dict[str, Any] | None = None,
        research_date: date | None = None,
    ) -> MarketResearch:
        """Create a market research entry.

        Args:
            tenant_id: Tenant scope.
            industry: Industry or vertical.
            trends: Detected trends array.
            market_size: TAM/SAM/SOM estimates.
            audience_insights: Audience behavior findings.
            competitive_landscape: Competitor positioning.
            research_date: Date of research.

        Returns:
            Created MarketResearch.
        """
        entry = MarketResearch.objects.create(
            tenant_id=tenant_id,
            industry=industry,
            trends=trends or [],
            market_size=market_size or {},
            audience_insights=audience_insights or {},
            competitive_landscape=competitive_landscape or {},
            research_date=research_date or date.today(),
        )
        logger.info("Created market research %s for %s", entry.id, industry)
        return entry

    @staticmethod
    def detect_trends(
        tenant_id: str,
        industry: str,
        sources: list[str] | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[dict[str, Any]]:
        """Detect trends from competitor content and market data.

        Uses keyword velocity and acceleration analysis on scraped content
        to identify emerging, peaking, and declining topics.

        Args:
            tenant_id: Tenant scope.
            industry: Industry to analyze.
            sources: Data sources to use.
            date_from: Analysis start date.
            date_to: Analysis end date.

        Returns:
            List of trends sorted by trend score.
        """
        date_to = date_to or date.today()
        date_from = date_from or (date_to - timedelta(days=90))

        # Gather content from competitors
        contents = CompetitorContent.objects.filter(
            competitor__tenant_id=tenant_id,
            competitor__is_active=True,
            published_at__date__gte=date_from,
            published_at__date__lte=date_to,
        ).select_related("competitor")

        # Extract all topics with daily counts
        topic_daily: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        topic_sources: dict[str, list[str]] = defaultdict(list)

        for content in contents:
            day = content.published_at.strftime("%Y-%m-%d") if content.published_at else ""
            for topic in content.topics or []:
                topic_daily[topic][day] += 1
                topic_sources[topic].append(content.platform)

        if not topic_daily:
            return []

        # Build daily counts series
        trends: list[dict[str, Any]] = []
        all_days = sorted({
            d for td in topic_daily.values() for d in td.keys()
        })
        if len(all_days) < 2:
            all_days = [
                (date_from + timedelta(days=i)).isoformat()
                for i in range((date_to - date_from).days + 1)
            ]

        for topic, daily in topic_daily.items():
            counts = [daily.get(d, 0) for d in all_days]
            total_volume = sum(counts)

            # Velocity: mean daily change
            diffs = [counts[i] - counts[i - 1] for i in range(1, len(counts))]
            velocity = statistics.mean(diffs) if diffs else 0

            # Acceleration: mean change in velocity
            accel_diffs = [diffs[i] - diffs[i - 1] for i in range(1, len(diffs))] if len(diffs) > 1 else []
            acceleration = statistics.mean(accel_diffs) if accel_diffs else 0

            # Lifecycle stage
            if acceleration > 0 and velocity > 0:
                stage = "emerging"
            elif acceleration <= 0 and velocity > 0:
                stage = "peaking"
            elif velocity <= 0:
                stage = "declining"
            else:
                stage = "stable"

            # Normalize metrics
            max_vol = max(sum(topic_daily[t].values()) for t in topic_daily) or 1
            max_vel = max(
                abs(statistics.mean(
                    [topic_daily[t].get(all_days[i], 0) - topic_daily[t].get(all_days[i - 1], 0)
                     for i in range(1, len(all_days))]
                ) if len(all_days) > 1 else 0 for t in topic_daily)
            ) or 1
            max_accel = max(
                abs(acceleration) for t, td in topic_daily.items()
                for acc in [ResearchService._calc_acceleration(
                    [td.get(d, 0) for d in all_days],
                )]
            ) or 1

            norm_vel = velocity / max_vel if max_vel else 0
            norm_accel = acceleration / max_accel if max_accel else 0
            norm_vol = total_volume / max_vol

            # Trend score
            trend_score = (norm_vel * 0.4) + (norm_accel * 0.3) + (norm_vol * 0.3)

            sources_list = list(set(topic_sources.get(topic, [])))

            trends.append({
                "name": topic,
                "velocity": round(velocity, 4),
                "acceleration": round(acceleration, 4),
                "volume": total_volume,
                "trend_score": round(trend_score, 4),
                "stage": stage,
                "sources": sources_list,
                "daily_counts": dict(sorted(daily.items())),
            })

        trends.sort(key=lambda t: t["trend_score"], reverse=True)
        return trends

    @staticmethod
    def _calc_acceleration(counts: list[int]) -> float:
        """Calculate acceleration from a count series."""
        diffs = [counts[i] - counts[i - 1] for i in range(1, len(counts))]
        if len(diffs) < 2:
            return 0.0
        accel_diffs = [diffs[i] - diffs[i - 1] for i in range(1, len(diffs))]
        return statistics.mean(accel_diffs) if accel_diffs else 0.0

    @staticmethod
    def estimate_market_size(
        industry: str,
        tam_source: str = "industry_report",
        geo_scope: str = "global",
    ) -> dict[str, Any]:
        """Estimate market size (TAM/SAM/SOM).

        Args:
            industry: Industry name.
            tam_source: Source for TAM data.
            geo_scope: Geographic scope.

        Returns:
            Market size estimate dict.
        """
        # In production: integrate with market data APIs.
        # Placeholder values use realistic scaling ratios.
        return {
            "industry": industry,
            "geo_scope": geo_scope,
            "tam": {
                "value": None,
                "currency": "USD",
                "year": date.today().year,
                "source": tam_source,
                "status": "needs_external_data",
            },
            "sam_ratio": 0.25,
            "som_ratio": 0.05,
            "methodology": "TAM from industry reports; SAM = TAM * 25%; SOM = TAM * 5%",
            "note": "Populate TAM.value with external market data source",
        }

    @staticmethod
    def aggregate_competitive_landscape(
        tenant_id: str,
    ) -> dict[str, Any]:
        """Build a competitive landscape summary from tracked competitors.

        Args:
            tenant_id: Tenant scope.

        Returns:
            Landscape dict with competitor summaries.
        """
        competitors = CompetitorProfile.objects.filter(
            tenant_id=tenant_id,
            is_active=True,
        )

        landscape = {
            "competitor_count": competitors.count(),
            "competitors": [],
            "platform_coverage": defaultdict(int),
            "total_tracked_content": 0,
        }

        for comp in competitors:
            social = comp.social_profiles or {}
            total_followers = 0
            for platform, data in social.items():
                if isinstance(data, dict):
                    total_followers += int(
                        data.get("followers", 0) or data.get("subscribers", 0) or 0,
                    )
                    landscape["platform_coverage"][platform] += 1

            content_count = CompetitorContent.objects.filter(
                competitor=comp,
            ).count()
            landscape["total_tracked_content"] += content_count

            landscape["competitors"].append({
                "id": str(comp.id),
                "name": comp.name,
                "website": comp.website,
                "total_followers": total_followers,
                "social_platforms": list(social.keys()),
                "content_pieces_tracked": content_count,
                "last_scraped": comp.last_scraped_at.isoformat() if comp.last_scraped_at else None,
            })

        landscape["platform_coverage"] = dict(landscape["platform_coverage"])
        return landscape
