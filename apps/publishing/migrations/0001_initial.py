# Generated initial migration for publishing


from django.db import migrations, models


class ApprovalStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    NOT_REQUIRED = "not_required", "Not Required"


class CalendarView(models.TextChoices):
    DAY = "day", "Day"
    WEEK = "week", "Week"
    MONTH = "month", "Month"
    QUARTER = "quarter", "Quarter"


class OverflowReason(models.TextChoices):
    FREQUENCY_LIMIT = "frequency_limit", "Frequency Limit"
    BLACKOUT_WINDOW = "blackout_window", "Blackout Window"
    RATE_LIMIT = "rate_limit", "Platform Rate Limit"
    QUEUE_FULL = "queue_full", "Queue Full"
    MANUAL = "manual", "Manual Overflow"


class Platform(models.TextChoices):
    INSTAGRAM = "instagram", "Instagram"
    LINKEDIN = "linkedin", "LinkedIn"
    TWITTER = "twitter", "Twitter / X"
    TIKTOK = "tiktok", "TikTok"
    YOUTUBE = "youtube", "YouTube"
    PINTEREST = "pinterest", "Pinterest"
    FACEBOOK = "facebook", "Facebook"
    THREADS = "threads", "Threads"


class Priority(models.IntegerChoices):
    URGENT = 0, "Urgent"
    HIGH = 1, "High"
    MEDIUM = 2, "Medium"
    LOW = 3, "Low"


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


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ScheduledPost",
            fields=[
                (
                    "content_id",
                    models.UUIDField(
                        null=True,
                        blank=True,
                        db_index=True,
                        help_text="Reference to content generation",
                    ),
                ),
                (
                    "campaign_id",
                    models.UUIDField(
                        null=True,
                        blank=True,
                        db_index=True,
                        help_text="Reference to campaign",
                    ),
                ),
                (
                    "platform",
                    models.CharField(max_length=32, choices=Platform.choices, db_index=True),
                ),
                (
                    "account_id",
                    models.UUIDField(db_index=True, help_text="Platform connection UUID"),
                ),
                (
                    "publish_type",
                    models.CharField(
                        max_length=32,
                        choices=PublishType.choices,
                        default=PublishType.FEED,
                    ),
                ),
                ("caption", models.TextField(blank=True, help_text="Post caption / body text")),
                (
                    "hashtags",
                    models.JSONField(default=list, blank=True, help_text="List of hashtags"),
                ),
                (
                    "media_urls",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="List of media file URLs",
                    ),
                ),
                ("link", models.URLField(blank=True, help_text="URL to include in post")),
                ("alt_text", models.TextField(blank=True, help_text="Alt text for media")),
                (
                    "first_comment",
                    models.TextField(
                        blank=True,
                        help_text="First comment text (e.g. Instagram hashtag comment)",
                    ),
                ),
                (
                    "location_json",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text='Location object: {"name": str, "lat": float, "lng": float}',
                    ),
                ),
                ("scheduled_at", models.DateTimeField(db_index=True, help_text="When to publish")),
                (
                    "timezone",
                    models.CharField(
                        max_length=100,
                        default="UTC",
                        help_text="IANA timezone",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=32,
                        choices=Status.choices,
                        default=Status.DRAFT,
                        db_index=True,
                    ),
                ),
                (
                    "priority",
                    models.PositiveSmallIntegerField(
                        choices=Priority.choices,
                        default=Priority.LOW,
                        db_index=True,
                    ),
                ),
                (
                    "approval_workflow_id",
                    models.UUIDField(
                        null=True,
                        blank=True,
                        db_index=True,
                        help_text="Approval workflow UUID if required",
                    ),
                ),
                (
                    "approval_status",
                    models.CharField(
                        max_length=32,
                        choices=ApprovalStatus.choices,
                        default=ApprovalStatus.NOT_REQUIRED,
                    ),
                ),
                (
                    "platform_post_id",
                    models.CharField(
                        max_length=255,
                        blank=True,
                        db_index=True,
                        help_text="Platform-assigned post ID",
                    ),
                ),
                ("publish_attempts", models.PositiveIntegerField(default=0)),
                ("last_attempt_at", models.DateTimeField(null=True, blank=True)),
                ("last_error", models.TextField(blank=True)),
                ("published_at", models.DateTimeField(null=True, blank=True, db_index=True)),
                (
                    "metadata_json",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Platform-specific metadata",
                    ),
                ),
                (
                    "created_by",
                    models.CharField(
                        max_length=256,
                        db_index=True,
                        help_text="UUID of user who scheduled the post",
                    ),
                ),
                ("tags", models.JSONField(default=list, blank=True, help_text="Content tags")),
                (
                    "dedup_hash",
                    models.CharField(
                        max_length=64,
                        blank=True,
                        db_index=True,
                        help_text="SHA-256 hash of caption + media for duplicate detection",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_scheduled_post",
                "verbose_name": "Scheduled Post",
                "verbose_name_plural": "Scheduled Posts",
                "ordering": ["-scheduled_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "status", "scheduled_at"]),
                    models.Index(fields=["tenant_id", "platform", "account_id"]),
                    models.Index(fields=["tenant_id", "campaign_id"]),
                    models.Index(fields=["tenant_id", "created_by"]),
                    models.Index(fields=["status", "scheduled_at"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="PublishQueue",
            fields=[
                (
                    "scheduled_post",
                    models.OneToOneField(
                        to="ScheduledPost",
                        on_delete=models.CASCADE,
                        related_name="queue_entry",
                        db_index=True,
                    ),
                ),
                (
                    "queue_priority",
                    models.PositiveSmallIntegerField(
                        default=3,
                        db_index=True,
                        help_text="0=urgent, 1=high, 2=medium, 3=low",
                    ),
                ),
                ("retry_count", models.PositiveIntegerField(default=0)),
                (
                    "next_retry_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        db_index=True,
                        help_text="When to attempt next retry",
                    ),
                ),
                (
                    "error_log",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="List of error entries: [{timestamp, error, attempt}]",
                    ),
                ),
                (
                    "overflow_reason",
                    models.CharField(
                        max_length=32,
                        choices=OverflowReason.choices,
                        blank=True,
                        help_text="Why this post was overflowed",
                    ),
                ),
                (
                    "overflowed_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When overflow happened",
                    ),
                ),
                (
                    "processed_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When successfully processed",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_publish_queue",
                "verbose_name": "Publish Queue Entry",
                "verbose_name_plural": "Publish Queue Entries",
                "ordering": ["queue_priority", "next_retry_at"],
                "indexes": [
                    models.Index(fields=["queue_priority", "next_retry_at"]),
                    models.Index(fields=["scheduled_post", "processed_at"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="ContentCalendar",
            fields=[
                (
                    "scheduled_post",
                    models.OneToOneField(
                        to="ScheduledPost",
                        on_delete=models.CASCADE,
                        related_name="calendar_entry",
                    ),
                ),
                (
                    "calendar_view",
                    models.CharField(
                        max_length=16,
                        choices=CalendarView.choices,
                        default=CalendarView.MONTH,
                    ),
                ),
                (
                    "position_order",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Render order within a calendar cell",
                    ),
                ),
                (
                    "color_override",
                    models.CharField(
                        max_length=7,
                        blank=True,
                        help_text="Optional hex colour override (#RRGGBB)",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_content_calendar",
                "verbose_name": "Content Calendar Entry",
                "verbose_name_plural": "Content Calendar Entries",
                "ordering": ["scheduled_post__scheduled_at"],
                "indexes": [models.Index(fields=["tenant_id", "calendar_view"])],
            },
        ),
    ]
