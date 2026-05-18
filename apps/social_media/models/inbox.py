"""Unified inbox message model.

Aggregates messages, comments, DMs, and mentions from all connected
social platforms into a single normalized interface with threading,
assignment, and response tracking.
"""

from __future__ import annotations

from django.db import models

from apps.core.models import UUIDModel, TimeStampedModel, TenantModel


class InboxMessage(UUIDModel, TenantModel, TimeStampedModel):
    """A normalized message from any social platform.

    Attributes:
        platform: Source platform (instagram, linkedin, twitter, etc.)
        platform_message_id: Native ID from the platform.
        type: Message type — comment, dm, mention, review.
        author_name: Display name of the message author.
        author_platform_id: User ID on the source platform.
        author_avatar: URL to author profile image.
        text: Message body text.
        media_urls: List of attached media URLs.
        parent: Parent message for threaded replies.
        post_id: Reference to the original platform post.
        thread_id: Thread grouping UUID.
        sentiment: Detected sentiment label.
        sentiment_score: Numeric sentiment score (-1.0 to +1.0).
        spam_score: Spam detection score (0.0 to 1.0).
        status: Workflow status — new, read, replied, hidden, archived.
        assigned_to: User ID the message is assigned to.
        assignment_reason: Why this message was auto-assigned.
        replied_at: Timestamp when a reply was sent.
        response_time_minutes: Minutes between receipt and reply.
        received_at: When the message was first seen on the platform.
    """

    MESSAGE_TYPES = [
        ("comment", "Comment"),
        ("dm", "Direct Message"),
        ("mention", "Mention"),
        ("review", "Review"),
    ]

    STATUSES = [
        ("new", "New"),
        ("read", "Read"),
        ("replied", "Replied"),
        ("hidden", "Hidden"),
        ("archived", "Archived"),
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
        ("pinterest", "Pinterest"),
        ("reddit", "Reddit"),
        ("threads", "Threads"),
    ]

    platform = models.CharField(max_length=50, choices=PLATFORMS, db_index=True)
    platform_message_id = models.CharField(max_length=255, blank=True, db_index=True)
    type = models.CharField(max_length=30, choices=MESSAGE_TYPES, db_index=True)
    author_name = models.CharField(max_length=255, blank=True)
    author_platform_id = models.CharField(max_length=255, blank=True, db_index=True)
    author_avatar = models.URLField(blank=True)
    text = models.TextField(blank=True)
    media_urls = models.JSONField(default=list, blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies",
        help_text="Parent message for threaded replies",
    )
    post_id = models.CharField(max_length=255, blank=True, db_index=True)
    thread_id = models.UUIDField(null=True, blank=True, db_index=True)
    sentiment = models.CharField(max_length=20, choices=SENTIMENTS, blank=True, db_index=True)
    sentiment_score = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    spam_score = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="new", db_index=True)
    assigned_to = models.CharField(max_length=128, blank=True, db_index=True)
    assignment_reason = models.TextField(blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)
    response_time_minutes = models.PositiveIntegerField(null=True, blank=True)
    received_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = "sm_inbox_messages"
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["tenant_id", "received_at"]),
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "platform", "status"]),
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["thread_id"]),
            models.Index(fields=["tenant_id", "type", "status"]),
        ]

    def __str__(self) -> str:
        return f"[{self.platform}] {self.type}: {self.author_name}"
