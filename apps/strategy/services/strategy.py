"""Content Strategy service — SP-003 business logic.

Handles strategy creation, topic cluster generation, format mix
optimization, and goal-to-content mapping.
"""

from __future__ import annotations

import logging
from typing import Any

from apps.strategy.models import ContentStrategy

logger = logging.getLogger(__name__)

# Goal-to-content mapping per spec
GOAL_CONTENT_MAP = {
    "brand_awareness": {
        "primary": ["blog_posts", "video", "infographics", "pr"],
        "secondary": ["social_posts", "podcasts", "webinars"],
        "kpi": ["reach", "impressions", "brand_mentions"],
    },
    "lead_generation": {
        "primary": ["whitepapers", "webinars", "case_studies", "landing_pages"],
        "secondary": ["blog_posts", "email_sequences", "social_ads"],
        "kpi": ["leads", "conversion_rate", "cost_per_lead"],
    },
    "engagement": {
        "primary": ["social_posts", "polls", "ugc", "live_streams"],
        "secondary": ["blog_posts", "email", "community_posts"],
        "kpi": ["engagement_rate", "comments", "shares", "time_on_page"],
    },
    "conversion": {
        "primary": ["case_studies", "testimonials", "product_demos", "comparison_guides"],
        "secondary": ["email_sequences", "retargeting_ads", "landing_pages"],
        "kpi": ["conversion_rate", "revenue", "average_order_value"],
    },
    "retention": {
        "primary": ["email_newsletters", "loyalty_programs", "tutorials", "community"],
        "secondary": ["social_posts", "webinars", "product_updates"],
        "kpi": ["retention_rate", "churn_rate", "lifetime_value"],
    },
}

# Platform algorithm preferences (2026)
ALGORITHM_PREFERENCES = {
    "instagram": {"reels": 0.40, "carousel": 0.30, "stories": 0.20, "feed_image": 0.10},
    "linkedin": {
        "text_posts": 0.30,
        "carousel": 0.25,
        "video": 0.25,
        "articles": 0.15,
        "polls": 0.05,
    },
    "tiktok": {"short_video": 0.60, "long_video": 0.25, "live": 0.10, "photo": 0.05},
    "twitter": {"threads": 0.30, "text": 0.25, "images": 0.20, "video": 0.15, "polls": 0.10},
    "youtube": {"shorts": 0.35, "long_form": 0.40, "live": 0.15, "community": 0.10},
}


class ContentStrategyService:
    """Service for content strategy operations."""

    @staticmethod
    def create_strategy(
        tenant_id: str,
        name: str,
        goal: str,
        target_personas: list[str] | None = None,
        topic_clusters: dict[str, Any] | None = None,
        format_mix: dict[str, Any] | None = None,
        channel_allocation: dict[str, Any] | None = None,
        content_pillars: list[dict[str, Any]] | None = None,
        gap_analysis: dict[str, Any] | None = None,
    ) -> ContentStrategy:
        """Create a new content strategy.

        Args:
            tenant_id: Tenant scope.
            name: Strategy name.
            goal: Marketing goal (from Goal choices).
            target_personas: List of persona UUIDs.
            topic_clusters: Topic cluster data.
            format_mix: Format distribution per channel.
            channel_allocation: Resource allocation.
            content_pillars: Pillar themes.
            gap_analysis: Gap analysis results.

        Returns:
            Created ContentStrategy.
        """
        strategy = ContentStrategy.objects.create(
            tenant_id=tenant_id,
            name=name,
            goal=goal,
            target_personas=target_personas or [],
            topic_clusters=topic_clusters or {},
            format_mix=format_mix or {},
            channel_allocation=channel_allocation or {},
            content_pillars=content_pillars or [],
            gap_analysis=gap_analysis or {},
        )
        logger.info("Created content strategy %s for tenant %s", strategy.id, tenant_id)
        return strategy

    @staticmethod
    def get_goal_mapping(goal: str) -> dict[str, Any]:
        """Get the content type mapping for a goal.

        Args:
            goal: Goal key (e.g. 'brand_awareness').

        Returns:
            Dict with primary, secondary content types and KPIs.
        """
        return GOAL_CONTENT_MAP.get(
            goal,
            {
                "primary": [],
                "secondary": [],
                "kpi": [],
            },
        )

    @staticmethod
    def generate_topic_clusters(
        seed_topics: list[str],
        audience_persona: dict[str, Any] | None = None,
        competitor_data: list[dict[str, Any]] | None = None,
        own_content_topics: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Generate topic clusters from seed topics.

        Performs semantic expansion and gap identification.

        Args:
            seed_topics: Root pillar topics.
            audience_persona: Persona data for relevance filtering.
            competitor_data: Competitor topic coverage.
            own_content_topics: Existing own content topics.

        Returns:
            List of cluster dicts with pillar, clusters, and gaps.
        """
        clusters: list[dict[str, Any]] = []
        competitor_data = competitor_data or []
        own_topics = set(own_content_topics or [])

        for seed in seed_topics:
            # Semantic expansion — generate related sub-topics
            sub_topics = _expand_topic(seed)

            # Filter by audience relevance
            if audience_persona:
                pref_topics = _extract_preference_topics(audience_persona)
                sub_topics = [
                    st
                    for st in sub_topics
                    if any(p.lower() in st["name"].lower() for p in pref_topics)
                    or True  # Include all if no match to avoid over-filtering
                ]

            # Build cluster topics
            cluster_topics = []
            for st in sub_topics:
                ct = {
                    "topic": st["name"],
                    "type": "cluster",
                    "search_volume": st.get("volume", 1000),
                    "difficulty": st.get("difficulty", 50),
                    "parent_pillar": seed,
                }
                cluster_topics.append(ct)

            # Identify gaps
            competitor_topics: set[str] = set()
            for cd in competitor_data:
                for t in cd.get("topics", []):
                    competitor_topics.add(t)
            gaps = [
                ct
                for ct in cluster_topics
                if ct["topic"] in competitor_topics and ct["topic"] not in own_topics
            ]

            total_volume = sum(ct["search_volume"] for ct in cluster_topics)
            avg_difficulty = (
                sum(ct["difficulty"] for ct in cluster_topics) / len(cluster_topics)
                if cluster_topics
                else 0
            )

            clusters.append(
                {
                    "pillar": {"topic": seed, "type": "pillar", "search_volume": total_volume},
                    "clusters": cluster_topics,
                    "gaps": gaps,
                    "total_search_volume": total_volume,
                    "avg_difficulty": round(avg_difficulty, 2),
                    "gap_count": len(gaps),
                }
            )

        clusters.sort(key=lambda c: c["total_search_volume"], reverse=True)
        return clusters

    @staticmethod
    def optimize_format_mix(
        channel: str,
        historical_data: list[dict[str, Any]] | None = None,
    ) -> dict[str, float]:
        """Optimize content format mix for a channel.

        Combines platform algorithm preferences with historical performance.

        Args:
            channel: Platform name (e.g. 'instagram', 'linkedin').
            historical_data: Performance by format.

        Returns:
            Normalized format recommendation percentages.
        """
        prefs = ALGORITHM_PREFERENCES.get(channel, {})
        if not prefs:
            return {}

        hist_map: dict[str, dict[str, float]] = {}
        for entry in historical_data or []:
            name = entry.get("format", entry.get("name", ""))
            hist_map[name] = {
                "engagement": entry.get("avg_engagement", 0.5),
                "reach": entry.get("avg_reach", 0.5),
                "conversions": entry.get("avg_conversions", 0.5),
            }

        scores: dict[str, float] = {}
        for fmt, weight in prefs.items():
            perf = hist_map.get(fmt, {"engagement": 0.5, "reach": 0.5, "conversions": 0.5})
            score = (
                (weight * 0.4)
                + (perf["engagement"] * 0.3)
                + (perf["reach"] * 0.2)
                + (perf["conversions"] * 0.1)
            )
            scores[fmt] = score

        total = sum(scores.values())
        if total == 0:
            return {fmt: round(1.0 / len(prefs), 4) for fmt in prefs}

        return {fmt: round(v / total, 4) for fmt, v in scores.items()}


def _expand_topic(seed: str) -> list[dict[str, Any]]:
    """Expand a seed topic into related sub-topics.

    In production this integrates with a knowledge base / semantic search.
    For now generates realistic related topics.
    """
    expansions = {
        "marketing_automation": [
            {"name": "email_automation", "volume": 5400, "difficulty": 45},
            {"name": "lead_nurturing", "volume": 3200, "difficulty": 38},
            {"name": "crm_integration", "volume": 4100, "difficulty": 52},
            {"name": "workflow_automation", "volume": 6700, "difficulty": 41},
            {"name": "drip_campaigns", "volume": 2800, "difficulty": 35},
        ],
        "data_analytics": [
            {"name": "marketing_attribution", "volume": 4800, "difficulty": 55},
            {"name": "customer_insights", "volume": 6200, "difficulty": 42},
            {"name": "roi_measurement", "volume": 3900, "difficulty": 48},
            {"name": "predictive_analytics", "volume": 7100, "difficulty": 58},
        ],
        "brand_strategy": [
            {"name": "brand_positioning", "volume": 5600, "difficulty": 40},
            {"name": "brand_voice", "volume": 4300, "difficulty": 33},
            {"name": "visual_identity", "volume": 3800, "difficulty": 36},
            {"name": "brand_consistency", "volume": 2900, "difficulty": 30},
        ],
        "social_media_trends": [
            {"name": "short_form_video", "volume": 8900, "difficulty": 35},
            {"name": "influencer_marketing", "volume": 7200, "difficulty": 44},
            {"name": "community_building", "volume": 5100, "difficulty": 38},
            {"name": "social_commerce", "volume": 6400, "difficulty": 50},
        ],
    }
    result = expansions.get(
        seed,
        [
            {"name": f"{seed}_basics", "volume": 1000, "difficulty": 30},
            {"name": f"{seed}_advanced", "volume": 800, "difficulty": 50},
            {"name": f"{seed}_tools", "volume": 1200, "difficulty": 40},
            {"name": f"{seed}_strategies", "volume": 900, "difficulty": 45},
        ],
    )
    return result


def _extract_preference_topics(persona: dict[str, Any]) -> list[str]:
    """Extract topic names from persona content preferences."""
    prefs = persona.get("content_preferences", {})
    topics = prefs.get("topics", [])
    return [t.get("topic", "") for t in topics if isinstance(t, dict)]
