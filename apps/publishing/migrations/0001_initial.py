"""Initial migration for Publishing module.

Creates ScheduledPost, PublishQueue, ContentCalendar, BlackoutWindow,
RecurringPost, ApprovalWorkflow, ApprovalInstance, ApprovalAction,
and PublishRetry models.
"""

from __future__ import annotations

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    """Initial migration."""

    initial = True

    dependencies = []

    operations = [
        # ScheduledPost
        migrations.CreateModel(
            name="ScheduledPost",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Globally unique identifier (UUID v4)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                        max_length=128,
                    ),
                ),
                (
                    "content_id",
                    models.UUIDField(
                        blank=True,
                        db_index=True,
                        help_text="Reference to content generation",
                        null=True,
                    ),
                ),
                (
                    "campaign_id",
                    models.UUIDField(
                        blank=True,
                        db_index=True,
                        help_text="Reference to campaign",
                        null=True,
                    ),
                ),
                (
                    "platform",
                    models.CharField(
                        choices=[
                            ("instagram", "Instagram"),
                            ("linkedin", "LinkedIn"),
                            ("twitter", "Twitter / X"),
                            ("tiktok", "TikTok"),
                            ("youtube", "YouTube"),
                            ("pinterest", "Pinterest"),
                            ("facebook", "Facebook"),
                            ("threads", "Threads"),
                        ],
                        db_index=True,
                        max_length=32,
                    ),
                ),
                (
                    "account_id",
                    models.UUIDField(
                        db_index=True,
                        help_text="Platform connection UUID",
                    ),
                ),
                (
                    "publish_type",
                    models.CharField(
                        choices=[
                            ("feed", "Feed"),
                            ("story", "Story"),
                            ("reel", "Reel"),
                            ("short", "Short"),
                            ("carousel", "Carousel"),
                        ],
                        default="feed",
                        max_length=32,
                    ),
                ),
                (
                    "caption",
                    models.TextField(blank=True, help_text="Post caption / body text"),
                ),
                (
                    "hashtags",
                    models.JSONField(blank=True, default=list, help_text="List of hashtags"),
                ),
                (
                    "media_urls",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="List of media file URLs",
                    ),
                ),
                (
                    "link",
                    models.URLField(blank=True, help_text="URL to include in post"),
                ),
                (
                    "alt_text",
                    models.TextField(blank=True, help_text="Alt text for media"),
                ),
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
                        blank=True,
                        default=dict,
                        help_text='Location: {"name": str, "lat": float, "lng": float}',
                    ),
                ),
                (
                    "scheduled_at",
                    models.DateTimeField(db_index=True, help_text="When to publish"),
                ),
                (
                    "timezone",
                    models.CharField(
                        default="UTC",
                        help_text="IANA timezone",
                        max_length=100,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("pending_approval", "Pending Approval"),
                            ("approved", "Approved"),
                            ("scheduled", "Scheduled"),
                            ("publishing", "Publishing"),
                            ("published", "Published"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        db_index=True,
                        default="draft",
                        max_length=32,
                    ),
                ),
                (
                    "priority",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (0, "Urgent"),
                            (1, "High"),
                            (2, "Medium"),
                            (3, "Low"),
                        ],
                        db_index=True,
                        default=3,
                    ),
                ),
                (
                    "approval_workflow_id",
                    models.UUIDField(
                        blank=True,
                        db_index=True,
                        help_text="Approval workflow UUID if required",
                        null=True,
                    ),
                ),
                (
                    "approval_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("not_required", "Not Required"),
                        ],
                        default="not_required",
                        max_length=32,
                    ),
                ),
                (
                    "platform_post_id",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        help_text="Platform-assigned post ID",
                        max_length=255,
                    ),
                ),
                (
                    "publish_attempts",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "last_attempt_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "last_error",
                    models.TextField(blank=True),
                ),
                (
                    "published_at",
                    models.DateTimeField(blank=True, db_index=True, null=True),
                ),
                (
                    "metadata_json",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Platform-specific metadata",
                    ),
                ),
                (
                    "created_by",
                    models.CharField(
                        db_index=True,
                        help_text="UUID of user who scheduled the post",
                        max_length=256,
                    ),
                ),
                (
                    "tags",
                    models.JSONField(blank=True, default=list, help_text="Content tags"),
                ),
                (
                    "dedup_hash",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        help_text="SHA-256 hash of caption + media for duplicate detection",
                        max_length=64,
                    ),
                ),
            ],
            options={
                "verbose_name": "Scheduled Post",
                "verbose_name_plural": "Scheduled Posts",
                "db_table": "voyager_scheduled_post",
                "ordering": ["-scheduled_at"],
            },
        ),
        migrations.AddIndex(
            model_name="scheduledpost",
            index=models.Index(
                fields=["tenant_id", "status", "scheduled_at"],
                name="voy_schpost_tenant_sts_sched",
            ),
        ),
        migrations.AddIndex(
            model_name="scheduledpost",
            index=models.Index(
                fields=["tenant_id", "platform", "account_id"],
                name="voy_schpost_tenant_plat_acct",
            ),
        ),
        migrations.AddIndex(
            model_name="scheduledpost",
            index=models.Index(
                fields=["tenant_id", "campaign_id"],
                name="voy_schpost_tenant_camp",
            ),
        ),
        migrations.AddIndex(
            model_name="scheduledpost",
            index=models.Index(
                fields=["tenant_id", "created_by"],
                name="voy_schpost_tenant_creator",
            ),
        ),
        migrations.AddIndex(
            model_name="scheduledpost",
            index=models.Index(
                fields=["status", "scheduled_at"],
                name="voy_schpost_status_sched",
            ),
        ),
        # PublishQueue
        migrations.CreateModel(
            name="PublishQueue",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Globally unique identifier (UUID v4)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "queue_priority",
                    models.PositiveSmallIntegerField(
                        db_index=True,
                        default=3,
                        help_text="0=urgent, 1=high, 2=medium, 3=low",
                    ),
                ),
                (
                    "retry_count",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "next_retry_at",
                    models.DateTimeField(
                        blank=True,
                        db_index=True,
                        help_text="When to attempt next retry",
                        null=True,
                    ),
                ),
                (
                    "error_log",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="List of error entries",
                    ),
                ),
                (
                    "overflow_reason",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("frequency_limit", "Frequency Limit"),
                            ("blackout_window", "Blackout Window"),
                            ("rate_limit", "Platform Rate Limit"),
                            ("queue_full", "Queue Full"),
                            ("manual", "Manual Overflow"),
                        ],
                        help_text="Why this post was overflowed",
                        max_length=32,
                    ),
                ),
                (
                    "overflowed_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When overflow happened",
                        null=True,
                    ),
                ),
                (
                    "processed_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When successfully processed",
                        null=True,
                    ),
                ),
                (
                    "scheduled_post",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="queue_entry",
                        to="publishing.scheduledpost",
                    ),
                ),
            ],
            options={
                "verbose_name": "Publish Queue Entry",
                "verbose_name_plural": "Publish Queue Entries",
                "db_table": "voyager_publish_queue",
                "ordering": ["queue_priority", "next_retry_at"],
            },
        ),
        migrations.AddIndex(
            model_name="publishqueue",
            index=models.Index(
                fields=["queue_priority", "next_retry_at"],
                name="voy_pubq_pri_retry",
            ),
        ),
        migrations.AddIndex(
            model_name="publishqueue",
            index=models.Index(
                fields=["scheduled_post", "processed_at"],
                name="voy_pubq_post_proc",
            ),
        ),
        # ContentCalendar
        migrations.CreateModel(
            name="ContentCalendar",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Globally unique identifier (UUID v4)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                        max_length=128,
                    ),
                ),
                (
                    "calendar_view",
                    models.CharField(
                        choices=[
                            ("day", "Day"),
                            ("week", "Week"),
                            ("month", "Month"),
                            ("quarter", "Quarter"),
                        ],
                        default="month",
                        max_length=16,
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
                        blank=True,
                        help_text="Optional hex colour override (#RRGGBB)",
                        max_length=7,
                    ),
                ),
                (
                    "scheduled_post",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="calendar_entry",
                        to="publishing.scheduledpost",
                    ),
                ),
            ],
            options={
                "verbose_name": "Content Calendar Entry",
                "verbose_name_plural": "Content Calendar Entries",
                "db_table": "voyager_content_calendar",
                "ordering": ["scheduled_post__scheduled_at"],
            },
        ),
        migrations.AddIndex(
            model_name="contentcalendar",
            index=models.Index(
                fields=["tenant_id", "calendar_view"],
                name="voy_cal_tenant_view",
            ),
        ),
        # BlackoutWindow
        migrations.CreateModel(
            name="BlackoutWindow",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Globally unique identifier (UUID v4)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                        max_length=128,
                    ),
                ),
                (
                    "name",
                    models.CharField(help_text="Blackout name", max_length=255),
                ),
                (
                    "account_id",
                    models.UUIDField(
                        blank=True,
                        db_index=True,
                        help_text="Account scope; null = all accounts",
                        null=True,
                    ),
                ),
                (
                    "platform",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        help_text="Platform scope; blank = all platforms",
                        max_length=32,
                    ),
                ),
                (
                    "start_at",
                    models.DateTimeField(help_text="Blackout start"),
                ),
                (
                    "end_at",
                    models.DateTimeField(help_text="Blackout end"),
                ),
                (
                    "recurring",
                    models.CharField(
                        choices=[
                            ("none", "Does not repeat"),
                            ("daily", "Daily"),
                            ("weekly", "Weekly"),
                            ("monthly", "Monthly"),
                        ],
                        default="none",
                        max_length=16,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(db_index=True, default=True),
                ),
                (
                    "metadata_json",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Additional blackout metadata",
                    ),
                ),
            ],
            options={
                "verbose_name": "Blackout Window",
                "verbose_name_plural": "Blackout Windows",
                "db_table": "voyager_blackout_window",
                "ordering": ["-start_at"],
            },
        ),
        migrations.AddIndex(
            model_name="blackoutwindow",
            index=models.Index(
                fields=["tenant_id", "account_id", "platform"],
                name="voy_bw_tenant_acct_plat",
            ),
        ),
        migrations.AddIndex(
            model_name="blackoutwindow",
            index=models.Index(
                fields=["tenant_id", "start_at", "end_at"],
                name="voy_bw_tenant_dates",
            ),
        ),
        migrations.AddIndex(
            model_name="blackoutwindow",
            index=models.Index(
                fields=["is_active", "start_at"],
                name="voy_bw_active_start",
            ),
        ),
        # RecurringPost
        migrations.CreateModel(
            name="RecurringPost",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Globally unique identifier (UUID v4)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                        max_length=128,
                    ),
                ),
                (
                    "name",
                    models.CharField(help_text="Series name", max_length=512),
                ),
                (
                    "platform",
                    models.CharField(help_text="Target platform", max_length=32),
                ),
                (
                    "account_id",
                    models.UUIDField(
                        db_index=True,
                        help_text="Platform connection UUID",
                    ),
                ),
                (
                    "publish_type",
                    models.CharField(
                        default="feed",
                        help_text="Post type",
                        max_length=32,
                    ),
                ),
                (
                    "cron_expression",
                    models.CharField(
                        help_text="Cron expression for scheduling",
                        max_length=128,
                    ),
                ),
                (
                    "start_date",
                    models.DateTimeField(help_text="Series start date"),
                ),
                (
                    "end_date",
                    models.DateTimeField(
                        blank=True,
                        help_text="Optional series end",
                        null=True,
                    ),
                ),
                (
                    "timezone",
                    models.CharField(
                        default="UTC",
                        help_text="IANA timezone",
                        max_length=100,
                    ),
                ),
                (
                    "content_pool",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="List of content variations",
                    ),
                ),
                (
                    "variation_strategy",
                    models.CharField(
                        choices=[
                            ("round_robin", "Round Robin"),
                            ("random", "Random"),
                            ("performance", "Performance"),
                            ("ai_adapt", "AI Adapt"),
                        ],
                        default="round_robin",
                        max_length=32,
                    ),
                ),
                (
                    "base_content",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Base content template",
                    ),
                ),
                (
                    "context_json",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Extra context for AI adaptation",
                    ),
                ),
                (
                    "last_instance_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="Last generated instance timestamp",
                        null=True,
                    ),
                ),
                (
                    "last_instance_number",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Last generated instance number",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(db_index=True, default=True),
                ),
                (
                    "created_by",
                    models.CharField(
                        db_index=True,
                        help_text="User UUID",
                        max_length=256,
                    ),
                ),
            ],
            options={
                "verbose_name": "Recurring Post",
                "verbose_name_plural": "Recurring Posts",
                "db_table": "voyager_recurring_post",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="recurringpost",
            index=models.Index(
                fields=["tenant_id", "is_active"],
                name="voy_recpost_tenant_active",
            ),
        ),
        migrations.AddIndex(
            model_name="recurringpost",
            index=models.Index(
                fields=["tenant_id", "platform", "account_id"],
                name="voy_recpost_tenant_plat_acct",
            ),
        ),
        migrations.AddIndex(
            model_name="recurringpost",
            index=models.Index(
                fields=["is_active", "start_date"],
                name="voy_recpost_active_start",
            ),
        ),
        # ApprovalWorkflow
        migrations.CreateModel(
            name="ApprovalWorkflow",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Globally unique identifier (UUID v4)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                        max_length=128,
                    ),
                ),
                (
                    "name",
                    models.CharField(help_text="Workflow name", max_length=255),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("sequential", "Sequential"),
                            ("parallel", "Parallel"),
                            ("conditional", "Conditional"),
                        ],
                        help_text="Approval type",
                        max_length=16,
                    ),
                ),
                (
                    "steps_json",
                    models.JSONField(
                        default=list,
                        help_text="Step definitions: [{step, name, approvers, timeoutHours, escalateTo, actions, condition}]",
                    ),
                ),
                (
                    "auto_approve_on_timeout",
                    models.BooleanField(
                        default=False,
                        help_text="Auto-approve after 2x step timeout",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(db_index=True, default=True),
                ),
                (
                    "created_by",
                    models.CharField(
                        db_index=True,
                        help_text="User UUID",
                        max_length=256,
                    ),
                ),
            ],
            options={
                "verbose_name": "Approval Workflow",
                "verbose_name_plural": "Approval Workflows",
                "db_table": "voyager_approval_workflow",
                "ordering": ["-created_at"],
            },
        ),
        # ApprovalInstance
        migrations.CreateModel(
            name="ApprovalInstance",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Globally unique identifier (UUID v4)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "current_step",
                    models.PositiveIntegerField(
                        default=1,
                        help_text="Current step number (1-indexed)",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("expired", "Expired"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=16,
                    ),
                ),
                (
                    "step_started_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        help_text="When current step started",
                    ),
                ),
                (
                    "completed_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "escalated_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "scheduled_post",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="approval_instance",
                        to="publishing.scheduledpost",
                    ),
                ),
                (
                    "workflow",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="instances",
                        to="publishing.approvalworkflow",
                    ),
                ),
            ],
            options={
                "verbose_name": "Approval Instance",
                "verbose_name_plural": "Approval Instances",
                "db_table": "voyager_approval_instance",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="approvalinstance",
            index=models.Index(
                fields=["workflow", "status"],
                name="voy_appinst_wf_status",
            ),
        ),
        migrations.AddIndex(
            model_name="approvalinstance",
            index=models.Index(
                fields=["scheduled_post", "status"],
                name="voy_appinst_post_status",
            ),
        ),
        # ApprovalAction
        migrations.CreateModel(
            name="ApprovalAction",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Globally unique identifier (UUID v4)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "step",
                    models.PositiveIntegerField(help_text="Step number"),
                ),
                (
                    "approver_id",
                    models.CharField(
                        db_index=True,
                        help_text="User UUID",
                        max_length=256,
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("approve", "Approve"),
                            ("reject", "Reject"),
                            ("request_changes", "Request Changes"),
                        ],
                        db_index=True,
                        max_length=32,
                    ),
                ),
                (
                    "comment",
                    models.TextField(blank=True),
                ),
                (
                    "instance",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="actions",
                        to="publishing.approvalinstance",
                    ),
                ),
            ],
            options={
                "verbose_name": "Approval Action",
                "verbose_name_plural": "Approval Actions",
                "db_table": "voyager_approval_action",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="approvalaction",
            index=models.Index(
                fields=["instance", "step"],
                name="voy_appact_inst_step",
            ),
        ),
        migrations.AddIndex(
            model_name="approvalaction",
            index=models.Index(
                fields=["approver_id", "action"],
                name="voy_appact_approver_action",
            ),
        ),
        # PublishRetry
        migrations.CreateModel(
            name="PublishRetry",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Globally unique identifier (UUID v4)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "attempt_number",
                    models.PositiveIntegerField(
                        db_index=True,
                        default=1,
                        help_text="Retry attempt number",
                    ),
                ),
                (
                    "error_type",
                    models.CharField(
                        choices=[
                            ("rate_limit", "Rate Limit"),
                            ("server_error", "Server Error"),
                            ("timeout", "Timeout"),
                            ("auth_expired", "Auth Expired"),
                            ("network", "Network Error"),
                            ("invalid_credentials", "Invalid Credentials"),
                            ("content_rejected", "Content Rejected"),
                            ("account_suspended", "Account Suspended"),
                            ("quota_exceeded", "Quota Exceeded"),
                            ("unknown", "Unknown"),
                        ],
                        db_index=True,
                        help_text="Classified error type",
                        max_length=32,
                    ),
                ),
                (
                    "error_message",
                    models.TextField(help_text="Full error message"),
                ),
                (
                    "platform_response_status",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="HTTP status from platform",
                        null=True,
                    ),
                ),
                (
                    "platform_response_body",
                    models.TextField(
                        blank=True,
                        help_text="Response body from platform",
                    ),
                ),
                (
                    "delay_seconds",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Calculated delay before retry",
                    ),
                ),
                (
                    "retried_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When retry was executed",
                        null=True,
                    ),
                ),
                (
                    "successful",
                    models.BooleanField(
                        db_index=True,
                        default=False,
                        help_text="Whether retry succeeded",
                    ),
                ),
                (
                    "scheduled_post",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="retries",
                        to="publishing.scheduledpost",
                    ),
                ),
            ],
            options={
                "verbose_name": "Publish Retry",
                "verbose_name_plural": "Publish Retries",
                "db_table": "voyager_publish_retry",
                "ordering": ["scheduled_post", "attempt_number"],
            },
        ),
        migrations.AddIndex(
            model_name="publishretry",
            index=models.Index(
                fields=["scheduled_post", "attempt_number"],
                name="voy_pubretry_post_attempt",
            ),
        ),
        migrations.AddIndex(
            model_name="publishretry",
            index=models.Index(
                fields=["error_type", "created_at"],
                name="voy_pubretry_err_created",
            ),
        ),
        migrations.AddIndex(
            model_name="publishretry",
            index=models.Index(
                fields=["successful", "created_at"],
                name="voy_pubretry_success_created",
            ),
        ),
    ]
