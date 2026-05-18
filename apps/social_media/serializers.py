"""Social Media request/response schemas.

Pydantic models for API input validation and response serialization.
All schemas used by Ninja view functions.
"""

from __future__ import annotations

from typing import Any

from ninja import Schema

# ---------------------------------------------------------------------------
# Inbox schemas
# ---------------------------------------------------------------------------


class InboxMessageIn(Schema):
    """Create a unified inbox message."""

    platform: str
    type: str
    text: str = ""
    author_name: str = ""
    author_platform_id: str = ""
    author_avatar: str = ""
    media_urls: list[str] = []
    parent_id: str | None = None
    post_id: str = ""
    thread_id: str | None = None
    received_at: str = ""


class InboxMessageOut(Schema):
    """Serialized inbox message."""

    id: str
    platform: str
    type: str
    author_name: str
    author_avatar: str
    text: str
    status: str
    sentiment: str
    sentiment_score: float
    spam_score: float
    assigned_to: str
    replied_at: str | None
    response_time_minutes: int | None
    received_at: str
    created_at: str


class InboxReplyIn(Schema):
    """Reply to an inbox message."""

    reply_text: str


class InboxAssignIn(Schema):
    """Assign an inbox message."""

    assigned_to: str
    assignment_reason: str = ""


# ---------------------------------------------------------------------------
# Comment schemas
# ---------------------------------------------------------------------------


class SocialCommentOut(Schema):
    """Serialized social comment."""

    id: str
    platform: str
    post_id: str
    author_name: str
    author_avatar: str
    text: str
    sentiment: str
    sentiment_score: float
    spam_score: float
    is_spam: bool
    is_hidden: bool
    moderation_action: str
    reply_text: str
    replied_at: str | None
    like_count: int
    received_at: str
    created_at: str


class CommentModerateIn(Schema):
    """Moderate a comment."""

    action: str
    reason: str = ""


class CommentReplyIn(Schema):
    """Reply to a comment."""

    reply_text: str


class BulkModerateIn(Schema):
    """Bulk moderate comments."""

    ids: list[str]
    action: str
    reason: str = ""


class ResponseSuggestIn(Schema):
    """Get AI response suggestions."""

    comment_text: str
    brand_tone: str = "professional"


# ---------------------------------------------------------------------------
# Community schemas
# ---------------------------------------------------------------------------


class CommunityMemberOut(Schema):
    """Serialized community member."""

    id: str
    platform: str
    name: str
    avatar: str
    bio: str
    followers: int
    following: int
    engagement_score: float
    influence_score: float
    loyalty_score: float
    vip_score: float
    tier: str
    first_seen_at: str
    last_active_at: str
    total_interactions: int


class EngagementScoreOut(Schema):
    """Engagement score result."""

    score: float
    tier: str
    breakdown: dict[str, int]
    days: int


class VIPListOut(Schema):
    """VIP member list by tier."""

    champions: list[CommunityMemberOut]
    advocates: list[CommunityMemberOut]
    engaged: list[CommunityMemberOut]


# ---------------------------------------------------------------------------
# Hashtag schemas
# ---------------------------------------------------------------------------


class HashtagResearchOut(Schema):
    """Serialized hashtag research record."""

    id: str
    hashtag: str
    platform: str
    total_posts: int
    posts_last_week: int
    posts_last_day: int
    avg_engagement: float
    competition_score: float
    opportunity_score: float
    recommendation: str
    trend_direction: str
    trend_percentage: float
    related_hashtags: list[str]
    category: str
    researched_at: str


class HashtagResearchIn(Schema):
    """Create a hashtag research record."""

    hashtag: str
    platform: str
    total_posts: int = 0
    posts_last_week: int = 0
    posts_last_day: int = 0
    avg_engagement: float = 0
    top_post_min_engagement: float = 0
    category: str = ""
    related_hashtags: list[str] = []


class HashtagScoreOut(Schema):
    """Hashtag competition score result."""

    hashtag: str
    platform: str
    competition: float
    opportunity: float
    recommendation: str
    metrics: dict[str, Any]


# ---------------------------------------------------------------------------
# Influencer schemas
# ---------------------------------------------------------------------------


class InfluencerProfileOut(Schema):
    """Serialized influencer profile."""

    id: str
    platform: str
    name: str
    avatar: str
    bio: str
    followers: int
    following: int
    engagement_rate: float
    niche: list[str]
    location: str
    authenticity_score: float
    rate_estimate: float
    content_quality_score: float
    match_score: float
    status: str
    outreach_status: str
    outreach_sent_at: str | None
    responded_at: str | None
    contact_email: str
    website: str
    created_at: str


class InfluencerSearchIn(Schema):
    """Search influencers."""

    niche: list[str] = []
    location: str = ""
    min_followers: int = 0
    max_followers: int = 0
    min_engagement: float = 0
    platforms: list[str] = []
    limit: int = 50


class OutreachUpdateIn(Schema):
    """Update outreach status."""

    status: str


# ---------------------------------------------------------------------------
# Listening schemas
# ---------------------------------------------------------------------------


class SocialMentionOut(Schema):
    """Serialized social mention."""

    id: str
    platform: str
    mention_type: str
    tracked_term: str
    author_name: str
    author_avatar: str
    author_followers: int
    text: str
    url: str
    sentiment: str
    sentiment_score: float
    influence_score: float
    reach_estimate: int
    language: str
    is_alert_triggered: bool
    alert_reason: str
    mentioned_at: str


class CollectMentionIn(Schema):
    """Collect a mention."""

    platform: str
    id: str = ""
    mention_type: str = "brand"
    tracked_term: str = ""
    author_name: str = ""
    author_id: str = ""
    author_avatar: str = ""
    author_followers: int = 0
    text: str = ""
    url: str = ""
    influence_score: float = 0
    reach_estimate: int = 0
    language: str = ""
    media_urls: list[str] = []
    created_at: str = ""


class SentimentAnalysisOut(Schema):
    """Sentiment analysis result."""

    sentiment: str
    score: float


class MentionSummaryOut(Schema):
    """Mention summary."""

    total_mentions: int
    sentiment_distribution: dict[str, int]
    alert_count: int
    by_platform: dict[str, int]
    by_tracked_term: dict[str, int]
    period_days: int


# ---------------------------------------------------------------------------
# Benchmarking schemas
# ---------------------------------------------------------------------------


class CompetitorBenchmarkOut(Schema):
    """Serialized competitor benchmark."""

    id: str
    platform: str
    competitor_name: str
    competitor_handle: str
    metric_period: str
    period_start: str
    period_end: str
    posts_count: int
    avg_engagement_rate: float
    avg_likes: int
    avg_comments: int
    avg_shares: int
    total_followers: int
    follower_growth: int
    engagement_diff: float
    follower_diff: int
    content_themes: list[str]


class BenchmarkIn(Schema):
    """Create a competitor benchmark."""

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
    competitor_content_themes: list[str] = []


class LeaderboardEntryOut(Schema):
    """Leaderboard entry."""

    rank: int
    competitor_name: str
    competitor_handle: str
    metric: str
    value: float
    period_end: str


class TrendDataPointOut(Schema):
    """Trend data point."""

    period_start: str
    period_end: str
    competitor_value: float
    brand_value: float
    diff: float
