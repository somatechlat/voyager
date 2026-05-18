"""Social comment model.

Stores comment replies, moderation actions, and sentiment analysis
for comments across all social platforms.
"""

from __future__ import annotations

from django.db import models

from .base import TenantModel, TimeStampedModel, UUIDModel


class SocialComment(UUIDModel, TenantModel, TimeStampedModel):
    """A comment on a social media post with moderation and reply tracking.

    Attributes:
        platform: Source platform.
        platform_comment_id: Native comment ID.
        post_id: The post this comment belongs to.
        parent_comment: Parent comment for threaded replies.
        author_name: Comment author display name.
        author_platform_id: Author user ID on the platform.
        author_avatar: URL to author profile image.
        text: Comment body text.
        sentiment: Detected sentiment label.
        sentiment_score: Numeric sentiment score (-1.0 to +1.0).
        spam_score: Spam detection score (0.0 to 1.0).
        spam_reasons: List of detected spam indicators.
        is_spam: Whether the comment is flagged as spam.
        is_hidden: Whether the comment is hidden from public view.
        hidden_reason: Reason for hiding.
        moderation_action: Action taken — none, hide, delete, flag.
        moderated_by: User who performed moderation.
        moderated_at: When moderation occurred.
        reply_text: Our reply text.
        replied_by: User who replied.
        replied_at: When the reply was sent.
        ai_suggestions: AI-generated response suggestions.
        like_count: Number of likes on the comment.
        received_at: When the comment was first seen.
    """

    MODERATION_ACTIONS = [
        ("none", "None"),
        ("hide", "Hide"),
        ("delete", "Delete"),
        ("flag", "Flag for Review"),
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
    ]

    platform = models.CharField(max_length=50, choices=PLATFORMS, db_index=True)
    platform_comment_id = models.CharField(max_length=255, blank=True, db_index=True)
    post_id = models.CharField(max_length=255, blank=True, db_index=True)
    parent_comment = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies",
    )
    author_name = models.CharField(max_length=255, blank=True)
    author_platform_id = models.CharField(max_length=255, blank=True, db_index=True)
    author_avatar = models.URLField(blank=True)
    text = models.TextField(blank=True)
    sentiment = models.CharField(max_length=20, choices=SENTIMENTS, blank=True, db_index=True)
    sentiment_score = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    spam_score = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    spam_reasons = models.JSONField(default=list, blank=True)
    is_spam = models.BooleanField(default=False, db_index=True)
    is_hidden = models.BooleanField(default=False, db_index=True)
    hidden_reason = models.TextField(blank=True)
    moderation_action = models.CharField(
        max_length=20, choices=MODERATION_ACTIONS, default="none", db_index=True
    )
    moderated_by = models.CharField(max_length=128, blank=True)
    moderated_at = models.DateTimeField(null=True, blank=True)
    reply_text = models.TextField(blank=True)
    replied_by = models.CharField(max_length=128, blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)
    ai_suggestions = models.JSONField(default=list, blank=True)
    like_count = models.PositiveIntegerField(default=0)
    received_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "sm_social_comments"
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["tenant_id", "post_id", "received_at"]),
            models.Index(fields=["tenant_id", "is_spam"]),
            models.Index(fields=["tenant_id", "is_hidden"]),
            models.Index(fields=["tenant_id", "platform", "received_at"]),
            models.Index(fields=["tenant_id", "sentiment", "spam_score"]),
        ]

    def __str__(self) -> str:
        return f"[{self.platform}] {self.author_name}: {self.text[:60]}"
