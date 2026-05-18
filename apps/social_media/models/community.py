"""Community member model.

Tracks community members across platforms with engagement scoring,
VIP tier classification, and influence metrics.
"""

from __future__ import annotations

from django.db import models

from .base import TenantModel, TimeStampedModel, UUIDModel


class CommunityMember(UUIDModel, TenantModel, TimeStampedModel):
    """A community member tracked across social platforms.

    Attributes:
        platform: Primary platform identifier.
        platform_user_id: Native user ID on the platform.
        name: Display name.
        avatar: Profile image URL.
        bio: Profile bio text.
        followers: Follower count.
        following: Following count.
        engagement_score: Weighted engagement score.
        influence_score: Influence/calculated percentile score.
        loyalty_score: Loyalty score based on consistency and tenure.
        vip_score: Composite VIP score (0-100).
        tier: VIP tier — champion, advocate, engaged, passive.
        first_seen_at: When this member was first observed.
        last_active_at: Most recent activity timestamp.
        total_interactions: Total number of interactions recorded.
        interaction_breakdown: JSON with per-type interaction counts.
    """

    TIERS = [
        ("champion", "Champion"),
        ("advocate", "Advocate"),
        ("engaged", "Engaged"),
        ("passive", "Passive"),
    ]

    PLATFORMS = [
        ("instagram", "Instagram"),
        ("linkedin", "LinkedIn"),
        ("twitter", "Twitter / X"),
        ("facebook", "Facebook"),
        ("tiktok", "TikTok"),
        ("youtube", "YouTube"),
        ("pinterest", "Pinterest"),
        ("reddit", "Reddit"),
        ("threads", "Threads"),
    ]

    platform = models.CharField(max_length=50, choices=PLATFORMS, db_index=True)
    platform_user_id = models.CharField(max_length=255, blank=True, db_index=True)
    name = models.CharField(max_length=255, blank=True, db_index=True)
    avatar = models.URLField(blank=True)
    bio = models.TextField(blank=True)
    followers = models.PositiveIntegerField(default=0)
    following = models.PositiveIntegerField(default=0)
    engagement_score = models.DecimalField(max_digits=8, decimal_places=2, default=0, db_index=True)
    influence_score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    loyalty_score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    vip_score = models.DecimalField(max_digits=8, decimal_places=2, default=0, db_index=True)
    tier = models.CharField(max_length=20, choices=TIERS, default="passive", db_index=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_active_at = models.DateTimeField(auto_now=True)
    total_interactions = models.PositiveIntegerField(default=0)
    interaction_breakdown = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "sm_community_members"
        ordering = ["-vip_score", "-engagement_score"]
        indexes = [
            models.Index(fields=["tenant_id", "vip_score"]),
            models.Index(fields=["tenant_id", "tier"]),
            models.Index(fields=["tenant_id", "platform", "vip_score"]),
            models.Index(fields=["tenant_id", "engagement_score"]),
            models.Index(fields=["tenant_id", "platform_user_id"]),
        ]
        unique_together = [("tenant_id", "platform", "platform_user_id")]

    def __str__(self) -> str:
        return f"{self.name} ({self.platform}) — {self.tier}"
