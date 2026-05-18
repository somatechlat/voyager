# Generated initial migration for social_media


from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="InboxMessage",
            fields=[
                ("platform", models.CharField(max_length=50, choices=PLATFORMS, db_index=True)),
                (
                    "platform_message_id",
                    models.CharField(max_length=255, blank=True, db_index=True),
                ),
                ("type", models.CharField(max_length=30, choices=MESSAGE_TYPES, db_index=True)),
                ("author_name", models.CharField(max_length=255, blank=True)),
                ("author_platform_id", models.CharField(max_length=255, blank=True, db_index=True)),
                ("author_avatar", models.URLField(blank=True)),
                ("text", models.TextField(blank=True)),
                ("media_urls", models.JSONField(default=list, blank=True)),
                (
                    "parent",
                    models.ForeignKey(
                        to="self",
                        on_delete=models.SET_NULL,
                        null=True,
                        blank=True,
                        related_name="replies",
                        help_text="Parent message for threaded replies",
                    ),
                ),
                ("post_id", models.CharField(max_length=255, blank=True, db_index=True)),
                ("thread_id", models.UUIDField(null=True, blank=True, db_index=True)),
                (
                    "sentiment",
                    models.CharField(
                        max_length=20,
                        choices=SENTIMENTS,
                        blank=True,
                        db_index=True,
                    ),
                ),
                (
                    "sentiment_score",
                    models.DecimalField(
                        max_digits=4,
                        decimal_places=3,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "spam_score",
                    models.DecimalField(
                        max_digits=3,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=STATUSES,
                        default="new",
                        db_index=True,
                    ),
                ),
                ("assigned_to", models.CharField(max_length=128, blank=True, db_index=True)),
                ("assignment_reason", models.TextField(blank=True)),
                ("replied_at", models.DateTimeField(null=True, blank=True)),
                ("response_time_minutes", models.PositiveIntegerField(null=True, blank=True)),
                ("received_at", models.DateTimeField(db_index=True)),
            ],
            options={
                "db_table": "sm_inbox_messages",
                "ordering": ["-received_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "received_at"]),
                    models.Index(fields=["tenant_id", "status"]),
                    models.Index(fields=["tenant_id", "platform", "status"]),
                    models.Index(fields=["assigned_to", "status"]),
                    models.Index(fields=["thread_id"]),
                    models.Index(fields=["tenant_id", "type", "status"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="SocialComment",
            fields=[
                ("platform", models.CharField(max_length=50, choices=PLATFORMS, db_index=True)),
                (
                    "platform_comment_id",
                    models.CharField(max_length=255, blank=True, db_index=True),
                ),
                ("post_id", models.CharField(max_length=255, blank=True, db_index=True)),
                (
                    "parent_comment",
                    models.ForeignKey(
                        to="self",
                        on_delete=models.SET_NULL,
                        null=True,
                        blank=True,
                        related_name="replies",
                    ),
                ),
                ("author_name", models.CharField(max_length=255, blank=True)),
                ("author_platform_id", models.CharField(max_length=255, blank=True, db_index=True)),
                ("author_avatar", models.URLField(blank=True)),
                ("text", models.TextField(blank=True)),
                (
                    "sentiment",
                    models.CharField(
                        max_length=20,
                        choices=SENTIMENTS,
                        blank=True,
                        db_index=True,
                    ),
                ),
                (
                    "sentiment_score",
                    models.DecimalField(
                        max_digits=4,
                        decimal_places=3,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "spam_score",
                    models.DecimalField(
                        max_digits=3,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                ("spam_reasons", models.JSONField(default=list, blank=True)),
                ("is_spam", models.BooleanField(default=False, db_index=True)),
                ("is_hidden", models.BooleanField(default=False, db_index=True)),
                ("hidden_reason", models.TextField(blank=True)),
                (
                    "moderation_action",
                    models.CharField(
                        max_length=20,
                        choices=MODERATION_ACTIONS,
                        default="none",
                        db_index=True,
                    ),
                ),
                ("moderated_by", models.CharField(max_length=128, blank=True)),
                ("moderated_at", models.DateTimeField(null=True, blank=True)),
                ("reply_text", models.TextField(blank=True)),
                ("replied_by", models.CharField(max_length=128, blank=True)),
                ("replied_at", models.DateTimeField(null=True, blank=True)),
                ("ai_suggestions", models.JSONField(default=list, blank=True)),
                ("like_count", models.PositiveIntegerField(default=0)),
                ("received_at", models.DateTimeField(db_index=True)),
            ],
            options={
                "db_table": "sm_social_comments",
                "ordering": ["-received_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "post_id", "received_at"]),
                    models.Index(fields=["tenant_id", "is_spam"]),
                    models.Index(fields=["tenant_id", "is_hidden"]),
                    models.Index(fields=["tenant_id", "platform", "received_at"]),
                    models.Index(fields=["tenant_id", "sentiment", "spam_score"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="CommunityMember",
            fields=[
                ("platform", models.CharField(max_length=50, choices=PLATFORMS, db_index=True)),
                ("platform_user_id", models.CharField(max_length=255, blank=True, db_index=True)),
                ("name", models.CharField(max_length=255, blank=True, db_index=True)),
                ("avatar", models.URLField(blank=True)),
                ("bio", models.TextField(blank=True)),
                ("followers", models.PositiveIntegerField(default=0)),
                ("following", models.PositiveIntegerField(default=0)),
                (
                    "engagement_score",
                    models.DecimalField(
                        max_digits=8,
                        decimal_places=2,
                        default=0,
                        db_index=True,
                    ),
                ),
                ("influence_score", models.DecimalField(max_digits=8, decimal_places=2, default=0)),
                ("loyalty_score", models.DecimalField(max_digits=8, decimal_places=2, default=0)),
                (
                    "vip_score",
                    models.DecimalField(
                        max_digits=8,
                        decimal_places=2,
                        default=0,
                        db_index=True,
                    ),
                ),
                (
                    "tier",
                    models.CharField(
                        max_length=20,
                        choices=TIERS,
                        default="passive",
                        db_index=True,
                    ),
                ),
                ("first_seen_at", models.DateTimeField(auto_now_add=True)),
                ("last_active_at", models.DateTimeField(auto_now=True)),
                ("total_interactions", models.PositiveIntegerField(default=0)),
                ("interaction_breakdown", models.JSONField(default=dict, blank=True)),
            ],
            options={
                "db_table": "sm_community_members",
                "ordering": ["-vip_score", "-engagement_score"],
                "indexes": [
                    models.Index(fields=["tenant_id", "vip_score"]),
                    models.Index(fields=["tenant_id", "tier"]),
                    models.Index(fields=["tenant_id", "platform", "vip_score"]),
                    models.Index(fields=["tenant_id", "engagement_score"]),
                    models.Index(fields=["tenant_id", "platform_user_id"]),
                ],
                "unique_together": [("tenant_id", "platform", "platform_user_id")],
            },
        ),
    ]
