"""Social listening models.

Defines SocialMention for brand mention monitoring and sentiment
tracking, and CompetitorBenchmark for performance comparison.
"""

from __future__ import annotations

from django.db import models

from .base import TenantModel, TimeStampedModel, UUIDModel


class SocialMention(UUIDModel, TenantModel, TimeStampedModel):
    """A social mention of a brand, keyword, or tracked topic.

    Attributes:
        platform: Source platform.
        platform_mention_id: Native mention ID.
        mention_type: Type — brand, keyword, hashtag, competitor.
        tracked_term: The term that triggered this mention.
        author_name: Author display name.
        author_platform_id: Author user ID.
        author_avatar: Author profile image URL.
        author_followers: Author follower count.
        text: Mention content.
        url: Direct URL to the mention.
        sentiment: Detected sentiment.
        sentiment_score: Numeric sentiment (-1.0 to +1.0).
        influence_score: Author influence score (0-100).
        reach_estimate: Estimated reach of the mention.
        language: Content language code.
        media_urls: Attached media.
        is_alert_triggered: Whether this triggered an alert.
        alert_reason: Why the alert was triggered.
        processed: Whether this mention has been processed.
        mentioned_at: When the mention was published.
    """

    MENTION_TYPES = [
        ("brand", "Brand"),
        ("keyword", "Keyword"),
        ("hashtag", "Hashtag"),
        ("competitor", "Competitor"),
    ]

    SENTIMENTS = [
        ("positive", "Positive"),
        ("neutral", "Neutral"),
        ("negative", "Negative"),
    ]

    PLATFORMS = [
        ("instagram", "Instagram"),
        ("linkedin", "LinkedIn"),
        ("twitter", "Twitter / X"),
        ("facebook", "Facebook"),
        ("tiktok", "TikTok"),
        ("youtube", "YouTube"),
        ("reddit", "Reddit"),
        ("threads", "Threads"),
        ("news", "News"),
        ("blog", "Blog"),
        ("forum", "Forum"),
    ]

    platform = models.CharField(max_length=50, choices=PLATFORMS, db_index=True)
    platform_mention_id = models.CharField(max_length=255, blank=True, db_index=True)
    mention_type = models.CharField(
        max_length=20, choices=MENTION_TYPES, db_index=True
    )
    tracked_term = models.CharField(max_length=255, db_index=True)
    author_name = models.CharField(max_length=255, blank=True)
    author_platform_id = models.CharField(max_length=255, blank=True)
    author_avatar = models.URLField(blank=True)
    author_followers = models.PositiveIntegerField(default=0)
    text = models.TextField(blank=True)
    url = models.URLField(blank=True)
    sentiment = models.CharField(
        max_length=20, choices=SENTIMENTS, blank=True, db_index=True
    )
    sentiment_score = models.DecimalField(
        max_digits=4, decimal_places=3, null=True, blank=True
    )
    influence_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    reach_estimate = models.PositiveIntegerField(default=0)
    language = models.CharField(max_length=10, blank=True)
    media_urls = models.JSONField(default=list, blank=True)
    is_alert_triggered = models.BooleanField(default=False, db_index=True)
    alert_reason = models.TextField(blank=True)
    processed = models.BooleanField(default=False, db_index=True)
    mentioned_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "sm_social_mentions"
        ordering = ["-mentioned_at"]
        indexes = [
            models.Index(fields=["tenant_id", "tracked_term", "mentioned_at"]),
            models.Index(fields=["tenant_id", "sentiment", "mentioned_at"]),
            models.Index(fields=["tenant_id", "platform", "mentioned_at"]),
            models.Index(fields=["tenant_id", "is_alert_triggered"]),
            models.Index(fields=["tenant_id", "mention_type"]),
            models.Index(fields=["tenant_id", "processed"]),
        ]

    def __str__(self) -> str:
        return f"[{self.platform}] {self.tracked_term}: {self.author_name}"


class CompetitorBenchmark(UUIDModel, TenantModel, TimeStampedModel):
    """Performance benchmark comparing a competitor against the brand.

    Attributes:
        platform: Source platform.
        competitor_name: Competitor brand/handle name.
        competitor_handle: Platform handle.
        competitor_avatar: Competitor profile image URL.
        metric_period: Period this benchmark covers — weekly, monthly.
        period_start: Start of comparison period.
        period_end: End of comparison period.
        posts_count: Competitor posts in period.
        avg_engagement_rate: Average engagement rate.
        avg_likes: Average likes per post.
        avg_comments: Average comments per post.
        avg_shares: Average shares per post.
        total_followers: Current follower count.
        follower_growth: Net follower growth in period.
        top_post_url: URL to top-performing post.
        top_post_engagement: Engagement on top post.
        brand_posts_count: Our posts in same period.
        brand_avg_engagement: Our avg engagement rate.
        brand_total_followers: Our follower count.
        brand_follower_growth: Our follower growth.
        engagement_diff: Engagement rate difference.
        follower_diff: Follower growth difference.
        content_themes: Detected themes in competitor content.
    """

    METRIC_PERIODS = [
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
    ]

    PLATFORMS = [
        ("instagram", "Instagram"),
        ("linkedin", "LinkedIn"),
        ("twitter", "Twitter / X"),
        ("facebook", "Facebook"),
        ("tiktok", "TikTok"),
        ("youtube", "YouTube"),
    ]

    platform = models.CharField(max_length=50, choices=PLATFORMS, db_index=True)
    competitor_name = models.CharField(max_length=255, blank=True)
    competitor_handle = models.CharField(max_length=255, blank=True, db_index=True)
    competitor_avatar = models.URLField(blank=True)
    metric_period = models.CharField(
        max_length=20, choices=METRIC_PERIODS, default="weekly"
    )
    period_start = models.DateField(db_index=True)
    period_end = models.DateField(db_index=True)
    posts_count = models.PositiveIntegerField(default=0)
    avg_engagement_rate = models.DecimalField(
        max_digits=5, decimal_places=4, null=True, blank=True
    )
    avg_likes = models.PositiveIntegerField(default=0)
    avg_comments = models.PositiveIntegerField(default=0)
    avg_shares = models.PositiveIntegerField(default=0)
    total_followers = models.PositiveIntegerField(default=0)
    follower_growth = models.IntegerField(default=0)
    top_post_url = models.URLField(blank=True)
    top_post_engagement = models.PositiveIntegerField(default=0)
    brand_posts_count = models.PositiveIntegerField(default=0)
    brand_avg_engagement = models.DecimalField(
        max_digits=5, decimal_places=4, null=True, blank=True
    )
    brand_total_followers = models.PositiveIntegerField(default=0)
    brand_follower_growth = models.IntegerField(default=0)
    engagement_diff = models.DecimalField(
        max_digits=6, decimal_places=4, null=True, blank=True
    )
    follower_diff = models.IntegerField(default=0)
    content_themes = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "sm_competitor_benchmarks"
        ordering = ["-period_end", "-engagement_diff"]
        indexes = [
            models.Index(fields=["tenant_id", "competitor_handle"]),
            models.Index(fields=["tenant_id", "platform", "period_end"]),
            models.Index(fields=["tenant_id", "metric_period"]),
        ]
        unique_together = [
            ("tenant_id", "platform", "competitor_handle", "metric_period", "period_start")
        ]

    def __str__(self) -> str:
        return f"{self.competitor_name} ({self.platform}) — {self.period_start}"
