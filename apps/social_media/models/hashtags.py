"""Hashtag research model.

Stores hashtag volume, competition scoring, trend analysis,
and platform-specific recommendation data.
"""

from __future__ import annotations

from django.db import models

from .base import TenantModel, TimeStampedModel, UUIDModel


class HashtagResearch(UUIDModel, TenantModel, TimeStampedModel):
    """A hashtag research record with competition and opportunity scoring.

    Attributes:
        hashtag: The hashtag string (without #).
        platform: Platform this research applies to.
        total_posts: Total posts using this hashtag.
        posts_last_week: Posts in the last 7 days.
        posts_last_day: Posts in the last 24 hours.
        avg_engagement: Average engagement per post with this hashtag.
        top_post_min_engagement: Minimum engagement to reach "top posts".
        competition_score: How competitive (0-100, higher = harder).
        opportunity_score: How good the opportunity (0-100).
        recommendation: Recommendation level.
        trend_direction: Whether trending up, down, or stable.
        trend_percentage: Trend percentage change.
        related_hashtags: Related hashtags discovered.
        category: Broad category/niche for the hashtag.
        researched_at: When this research was last updated.
    """

    RECOMMENDATIONS = [
        ("highly_recommended", "Highly Recommended"),
        ("recommended", "Recommended"),
        ("consider", "Consider"),
        ("avoid", "Avoid"),
    ]

    TRENDS = [
        ("rising", "Rising"),
        ("falling", "Falling"),
        ("stable", "Stable"),
        ("viral", "Viral"),
    ]

    PLATFORMS = [
        ("instagram", "Instagram"),
        ("linkedin", "LinkedIn"),
        ("twitter", "Twitter / X"),
        ("facebook", "Facebook"),
        ("tiktok", "TikTok"),
        ("youtube", "YouTube"),
        ("pinterest", "Pinterest"),
        ("threads", "Threads"),
    ]

    hashtag = models.CharField(max_length=255, db_index=True)
    platform = models.CharField(max_length=50, choices=PLATFORMS, db_index=True)
    total_posts = models.PositiveBigIntegerField(default=0)
    posts_last_week = models.PositiveIntegerField(default=0)
    posts_last_day = models.PositiveIntegerField(default=0)
    avg_engagement = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    top_post_min_engagement = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    competition_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    opportunity_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    recommendation = models.CharField(
        max_length=30, choices=RECOMMENDATIONS, blank=True, db_index=True
    )
    trend_direction = models.CharField(
        max_length=20, choices=TRENDS, blank=True, db_index=True
    )
    trend_percentage = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    related_hashtags = models.JSONField(default=list, blank=True)
    category = models.CharField(max_length=255, blank=True, db_index=True)
    researched_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sm_hashtag_research"
        ordering = ["-opportunity_score", "-posts_last_week"]
        indexes = [
            models.Index(fields=["tenant_id", "platform", "opportunity_score"]),
            models.Index(fields=["tenant_id", "recommendation"]),
            models.Index(fields=["tenant_id", "trend_direction"]),
            models.Index(fields=["tenant_id", "hashtag", "platform"]),
            models.Index(fields=["tenant_id", "category"]),
        ]
        unique_together = [("tenant_id", "hashtag", "platform")]

    def __str__(self) -> str:
        return f"#{self.hashtag} ({self.platform}) — {self.recommendation}"
