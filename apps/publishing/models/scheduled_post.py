"""ScheduledPost model — stores scheduled content for 7+ platforms.

Tracks content, media, scheduling, status, approval workflow linkage,
and publishing metadata for multi-platform distribution.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from .base import TenantModel, TimeStampedModel, UUIDModel


class ScheduledPost(UUIDModel, TimeStampedModel, TenantModel):
    """A single scheduled post entry for one platform.

    Attributes:
        content_id: Reference to content generation UUID.
        campaign_id: Optional campaign UUID.
        platform: Target platform (instagram, linkedin, twitter, etc.).
        account_id: Reference to platform connection UUID.
        publish_type: Feed, story, reel, short, etc.
        caption: Post caption / body text.
        hashtags: JSON list of hashtags.
        media_urls: JSON list of media file URLs.
        link: Optional URL to include in post.
        scheduled_at: When the post should go live.
        timezone: IANA timezone for the scheduled time.
        status: Current lifecycle state of the post.
        priority: 0=urgent, 1=high, 2=medium, 3=low.
        approval_workflow_id: Optional approval workflow UUID.
        approval_status: Pending, approved, rejected, etc.
        platform_post_id: Platform-assigned post ID after publishing.
        publish_attempts: Number of publish attempts made.
        last_attempt_at: Timestamp of last publish attempt.
        last_error: Error message from last failed attempt.
        published_at: Timestamp when successfully published.
        created_by: UUID of the user who scheduled the post.
    """

    class Platform(models.TextChoices):
        INSTAGRAM = "instagram", "Instagram"
        LINKEDIN = "linkedin", "LinkedIn"
        TWITTER = "twitter", "Twitter / X"
        TIKTOK = "tiktok", "TikTok"
        YOUTUBE = "youtube", "YouTube"
        PINTEREST = "pinterest", "Pinterest"
        FACEBOOK = "facebook", "Facebook"
        THREADS = "threads", "Threads"

    class PublishType(models.TextChoices):
        FEED = "feed", "Feed"
        STORY = "story", "Story"
        REEL = "reel", "Reel"
        SHORT = "short", "Short"
        CAROUSEL = "carousel", "Carousel"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        APPROVED = "approved", "Approved"
        SCHEDULED = "scheduled", "Scheduled"
        PUBLISHING = "publishing", "Publishing"
        PUBLISHED = "published", "Published"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    class Priority(models.IntegerChoices):
        URGENT = 0, "Urgent"
        HIGH = 1, "High"
        MEDIUM = 2, "Medium"
        LOW = 3, "Low"

    class ApprovalStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        NOT_REQUIRED = "not_required", "Not Required"

    # References
    content_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Reference to content generation",
    )
    campaign_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Reference to campaign",
    )

    # Platform config
    platform = models.CharField(
        max_length=32,
        choices=Platform.choices,
        db_index=True,
    )
    account_id = models.UUIDField(
        db_index=True,
        help_text="Platform connection UUID",
    )
    publish_type = models.CharField(
        max_length=32,
        choices=PublishType.choices,
        default=PublishType.FEED,
    )

    # Content
    caption = models.TextField(blank=True, help_text="Post caption / body text")
    hashtags = models.JSONField(default=list, blank=True, help_text="List of hashtags")
    media_urls = models.JSONField(
        default=list,
        blank=True,
        help_text="List of media file URLs",
    )
    link = models.URLField(blank=True, help_text="URL to include in post")
    alt_text = models.TextField(blank=True, help_text="Alt text for media")
    first_comment = models.TextField(
        blank=True,
        help_text="First comment text (e.g. Instagram hashtag comment)",
    )
    location_json = models.JSONField(
        default=dict,
        blank=True,
        help_text='Location object: {"name": str, "lat": float, "lng": float}',
    )

    # Scheduling
    scheduled_at = models.DateTimeField(db_index=True, help_text="When to publish")
    timezone = models.CharField(
        max_length=100,
        default="UTC",
        help_text="IANA timezone",
    )

    # Status
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    priority = models.PositiveSmallIntegerField(
        choices=Priority.choices,
        default=Priority.LOW,
        db_index=True,
    )

    # Approval
    approval_workflow_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Approval workflow UUID if required",
    )
    approval_status = models.CharField(
        max_length=32,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.NOT_REQUIRED,
    )

    # Publishing metadata
    platform_post_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Platform-assigned post ID",
    )
    publish_attempts = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)

    # Metadata
    metadata_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Platform-specific metadata",
    )
    created_by = models.CharField(
        max_length=256,
        db_index=True,
        help_text="UUID of user who scheduled the post",
    )
    tags = models.JSONField(default=list, blank=True, help_text="Content tags")

    # Dedup
    dedup_hash = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        help_text="SHA-256 hash of caption + media for duplicate detection",
    )

    class Meta:
        db_table = "voyager_scheduled_post"
        verbose_name = "Scheduled Post"
        verbose_name_plural = "Scheduled Posts"
        ordering = ["-scheduled_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status", "scheduled_at"]),
            models.Index(fields=["tenant_id", "platform", "account_id"]),
            models.Index(fields=["tenant_id", "campaign_id"]),
            models.Index(fields=["tenant_id", "created_by"]),
            models.Index(fields=["status", "scheduled_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.platform} — {self.caption[:50]} ({self.status})"

    def is_due(self) -> bool:
        """Check if this post is due for publishing."""
        return self.status == self.Status.SCHEDULED and self.scheduled_at <= timezone.now()

    def can_publish(self) -> bool:
        """Check if post can be published (approved and due)."""
        if self.status not in (self.Status.SCHEDULED, self.Status.APPROVED):
            return False
        if self.approval_status == self.ApprovalStatus.REJECTED:
            return False
        if self.approval_workflow_id and self.approval_status != self.ApprovalStatus.APPROVED:
            return False
        return True

    def record_attempt(self, error: str | None = None) -> None:
        """Record a publish attempt, optionally with error."""
        self.publish_attempts += 1
        self.last_attempt_at = timezone.now()
        if error:
            self.last_error = error
        self.save(update_fields=["publish_attempts", "last_attempt_at", "last_error"])

    def mark_published(self, platform_post_id: str) -> None:
        """Mark as successfully published."""
        self.status = self.Status.PUBLISHED
        self.platform_post_id = platform_post_id
        self.published_at = timezone.now()
        self.last_error = ""
        self.save(update_fields=["status", "platform_post_id", "published_at", "last_error"])

    def mark_failed(self, error: str) -> None:
        """Mark as failed with error."""
        self.status = self.Status.FAILED
        self.last_error = error
        self.last_attempt_at = timezone.now()
        self.save(update_fields=["status", "last_error", "last_attempt_at"])
