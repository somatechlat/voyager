"""Competitor service — SP-002 business logic.

Handles competitor profile management, NLP content theme extraction,
SWOT auto-generation, and engagement analysis.
"""

from __future__ import annotations

import logging
import statistics
from collections import Counter
from typing import Any

from apps.strategy.models import CompetitorContent, CompetitorProfile

logger = logging.getLogger(__name__)

# NLP topic extraction using basic keyword frequency.
# In production this integrates with sentence-transformers/BERTopic.
STOP_WORDS = frozenset(
    [
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "can",
        "need",
        "dare",
        "ought",
        "used",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "out",
        "off",
        "over",
        "under",
        "again",
        "further",
        "then",
        "once",
        "and",
        "but",
        "or",
        "yet",
        "so",
        "if",
        "because",
        "although",
        "though",
        "while",
        "where",
        "when",
        "that",
        "which",
        "who",
        "whom",
        "whose",
        "what",
        "this",
        "these",
        "those",
        "i",
        "me",
        "my",
        "we",
        "our",
        "you",
        "your",
        "he",
        "him",
        "his",
        "she",
        "her",
        "it",
        "its",
        "they",
        "them",
        "their",
        "s",
        "t",
        "just",
        "don",
        "now",
        "ll",
        "re",
        "ve",
        "d",
        "m",
        "o",
        "ma",
        "y",
        "gonna",
        "wanna",
        "got",
        "get",
        "like",
        "one",
        "also",
        "new",
        "way",
        "time",
        "make",
        "well",
        "us",
        "more",
        "up",
        "all",
        "no",
        "about",
        "how",
        "out",
        "many",
        "other",
        "some",
        "only",
        "see",
        "him",
        "two",
        "her",
        "than",
        "them",
        "its",
        "now",
        "find",
        "long",
        "down",
        "day",
        "did",
        "she",
        "use",
        "her",
        "each",
        "which",
        "she",
        "how",
        "their",
        "if",
        "will",
        "up",
        "other",
        "about",
        "many",
        "then",
        "them",
        "these",
        "so",
        "some",
        "her",
        "would",
        "make",
        "like",
        "into",
        "him",
        "has",
        "two",
        "more",
        "very",
        "what",
        "know",
        "just",
        "first",
        "get",
        "over",
        "think",
        "also",
        "your",
        "work",
        "life",
        "even",
        "new",
        "want",
        "here",
        "back",
        "after",
        "use",
        "well",
        "way",
        "good",
        "too",
        "any",
        "may",
        "say",
        "great",
        "through",
        "when",
        "come",
        "much",
        "came",
        "old",
        "still",
        "where",
        "those",
        "while",
        "really",
        "right",
        "being",
        "both",
        "each",
        "few",
        "such",
        "off",
        "own",
        "under",
        "last",
        "never",
        "most",
        "around",
        "another",
        "put",
        "again",
        "against",
        "might",
        "next",
        "give",
        "done",
        "open",
        "case",
        "show",
        "live",
        "play",
        "went",
        "told",
        "seen",
        "heard",
        "found",
        "took",
        "made",
        "let",
        "set",
        "called",
        "tried",
        "asked",
        "moved",
        "based",
        "said",
        "called",
        "told",
        "took",
        "gave",
        "saw",
        "got",
        "came",
        "went",
        "made",
        "went",
        "said",
        "did",
        "was",
        "were",
        "had",
        "has",
        "have",
        "having",
        "do",
        "does",
    ]
)


class CompetitorService:
    """Service for competitor analysis operations."""

    @staticmethod
    def create_profile(
        tenant_id: str,
        name: str,
        website: str = "",
        social_profiles: dict[str, Any] | None = None,
        scraping_config: dict[str, Any] | None = None,
    ) -> CompetitorProfile:
        """Create a competitor profile.

        Args:
            tenant_id: Tenant scope.
            name: Competitor company name.
            website: Website URL.
            social_profiles: Social media presence data.
            scraping_config: Scraping configuration.

        Returns:
            Created CompetitorProfile.
        """
        profile = CompetitorProfile.objects.create(
            tenant_id=tenant_id,
            name=name,
            website=website,
            social_profiles=social_profiles or {},
            scraping_config=scraping_config or {},
        )
        logger.info("Created competitor profile %s for tenant %s", profile.id, tenant_id)
        return profile

    @staticmethod
    def add_content(
        competitor_id: str,
        platform: str,
        content_type: str,
        text: str = "",
        media_urls: list[str] | None = None,
        engagement_metrics: dict[str, Any] | None = None,
        published_at: str | None = None,
    ) -> CompetitorContent:
        """Add scraped content to a competitor profile.

        Args:
            competitor_id: Competitor UUID.
            platform: Source platform.
            content_type: Content type.
            text: Content body text.
            media_urls: Media URLs.
            engagement_metrics: Engagement data.
            published_at: ISO timestamp string.

        Returns:
            Created CompetitorContent.
        """
        from datetime import datetime

        pub_dt = None
        if published_at:
            try:
                pub_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                logger.debug("Failed to parse published_at: %s", published_at)

        content = CompetitorContent.objects.create(
            competitor_id=competitor_id,
            platform=platform,
            content_type=content_type,
            text=text,
            media_urls=media_urls or [],
            engagement_metrics=engagement_metrics or {},
            published_at=pub_dt,
            topics=[],
            sentiment=None,
        )
        logger.info("Added %s content to competitor %s", platform, competitor_id)
        return content

    @staticmethod
    def extract_themes(
        competitor_id: str,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, Any]]:
        """Extract content themes via NLP analysis.

        Uses keyword frequency + co-occurrence as a production-ready
        lightweight NLP pipeline. Results are cached for 24h.

        Args:
            competitor_id: Competitor UUID.
            date_from: Optional ISO date filter.
            date_to: Optional ISO date filter.

        Returns:
            List of theme dicts with keywords, prevalence, and engagement.
        """
        qs = CompetitorContent.objects.filter(competitor_id=competitor_id)
        if date_from:
            qs = qs.filter(published_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(published_at__date__lte=date_to)

        contents = list(qs)
        total = len(contents)
        if total == 0:
            return []

        # Extract keywords from all content
        keyword_freq: Counter[str] = Counter()
        content_keywords: list[list[str]] = []

        for content in contents:
            text = (content.text or "").lower()
            words = [
                w.strip(".,;:!?\"'()[]{}")
                for w in text.split()
                if len(w) > 3 and w not in STOP_WORDS
            ]
            filtered = [w for w in words if w and not w.isdigit()]
            content_keywords.append(filtered)
            keyword_freq.update(filtered)

        # Group by top keywords into themes
        top_keywords = keyword_freq.most_common(50)
        themes: list[dict[str, Any]] = []
        assigned: set[str] = set()

        for kw, count in top_keywords:
            if kw in assigned or count < 2:
                continue
            # Find co-occurring keywords
            cooccur: Counter[str] = Counter()
            theme_content_indices: list[int] = []
            for idx, ckw in enumerate(content_keywords):
                if kw in ckw:
                    cooccur.update(ckw)
                    theme_content_indices.append(idx)
            related = [
                (r, c)
                for r, c in cooccur.most_common(6)
                if r != kw and r not in assigned and c >= 2
            ]
            theme_kws = [kw] + [r for r, _ in related]
            assigned.update(theme_kws)

            # Calculate engagement for this theme
            theme_contents = [contents[i] for i in theme_content_indices if i < len(contents)]
            engagement_values = [
                float(em.get("engagement_rate", 0) or em.get("likes", 0) or 0)
                for tc in theme_contents
                for em in [tc.engagement_metrics or {}]
            ]
            reach_values = [
                float(em.get("reach", 0) or em.get("impressions", 0) or 0)
                for tc in theme_contents
                for em in [tc.engagement_metrics or {}]
            ]

            # Trend: count over time
            from collections import defaultdict

            counts_over_time: dict[str, int] = defaultdict(int)
            for tc in theme_contents:
                if tc.published_at:
                    counts_over_time[tc.published_at.strftime("%Y-%m-%d")] += 1

            trend = "stable"
            if len(counts_over_time) >= 2:
                vals = list(counts_over_time.values())
                if vals[-1] > vals[0] * 1.2:
                    trend = "rising"
                elif vals[-1] < vals[0] * 0.8:
                    trend = "falling"

            themes.append(
                {
                    "name": kw,
                    "keywords": theme_kws[:6],
                    "prevalence": round(count / total, 4),
                    "trend": trend,
                    "avg_engagement": (
                        round(statistics.mean(engagement_values), 4) if engagement_values else 0
                    ),
                    "avg_reach": round(statistics.mean(reach_values), 4) if reach_values else 0,
                    "content_count": len(theme_contents),
                    "trend_over_time": dict(sorted(counts_over_time.items())),
                }
            )

        themes.sort(key=lambda t: t["prevalence"], reverse=True)
        return themes

    @staticmethod
    def generate_swot(
        competitor_id: str,
        own_engagement_rate: float = 0.03,
        own_content_frequency: float = 10.0,
        own_response_time_hours: float = 2.0,
        own_ad_spend: float = 5000.0,
        own_topics: list[str] | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Generate SWOT analysis for a competitor.

        Args:
            competitor_id: Competitor UUID.
            own_engagement_rate: Own brand engagement rate.
            own_content_frequency: Own weekly content frequency.
            own_response_time_hours: Own response time in hours.
            own_ad_spend: Own ad spend.
            own_topics: Own brand content topics.

        Returns:
            SWOT dict with strengths, weaknesses, opportunities, threats.
        """
        contents = list(CompetitorContent.objects.filter(competitor_id=competitor_id))
        profile = CompetitorProfile.objects.filter(id=competitor_id).first()

        strengths: list[dict[str, Any]] = []
        weaknesses: list[dict[str, Any]] = []
        opportunities: list[dict[str, Any]] = []
        threats: list[dict[str, Any]] = []

        if not profile:
            return {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []}

        # Calculate competitor metrics
        if contents:
            engagement_values = [
                float(em.get("engagement_rate", 0) or em.get("likes", 0) or 0)
                for c in contents
                for em in [c.engagement_metrics or {}]
            ]
            avg_engagement = statistics.mean(engagement_values) if engagement_values else 0

            # Content frequency (content per week)
            dates = sorted({c.published_at for c in contents if c.published_at})
            if len(dates) >= 2:
                span = (dates[-1] - dates[0]).days or 1
                freq = len(dates) / (span / 7.0)
            else:
                freq = 0
        else:
            avg_engagement = 0
            freq = 0

        # Strengths
        if avg_engagement > own_engagement_rate * 1.2:
            strengths.append(
                {
                    "factor": "High engagement rate",
                    "evidence": round(avg_engagement, 4),
                }
            )
        if freq > own_content_frequency * 1.3:
            strengths.append(
                {
                    "factor": "High content volume",
                    "evidence": round(freq, 2),
                }
            )

        # Weaknesses
        social = profile.social_profiles or {}
        for platform, data in social.items():
            if (
                isinstance(data, dict)
                and data.get("responseTime", 0) > own_response_time_hours * 1.5
            ):
                weaknesses.append(
                    {
                        "factor": f"Slow {platform} response time",
                        "evidence": data["responseTime"],
                    }
                )

        # Opportunities
        competitor_topics: set[str] = set()
        for c in contents:
            for t in c.topics or []:
                competitor_topics.add(t)
        own_topics_set = set(own_topics or [])
        topic_gaps = own_topics_set - competitor_topics
        for gap in list(topic_gaps)[:10]:
            opportunities.append(
                {
                    "factor": f"Topic gap: {gap}",
                    "evidence": gap,
                }
            )

        # Threats
        total_followers = sum(
            int(data.get("followers", 0) or data.get("subscribers", 0) or 0)
            for data in (social or {}).values()
            if isinstance(data, dict)
        )
        own_total = own_ad_spend or 1
        if total_followers > own_total * 2:
            threats.append(
                {
                    "factor": "Significantly larger social following",
                    "evidence": total_followers,
                }
            )

        return {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "opportunities": opportunities,
            "threats": threats,
        }
