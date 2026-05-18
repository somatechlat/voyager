"""Initial migration for Social Media module (part 1).

Creates InboxMessage and SocialComment tables.
"""

from __future__ import annotations

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Initial migration part 1."""

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="InboxMessage",
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
                ("platform", models.CharField(db_index=True, max_length=50)),
                (
                    "platform_message_id",
                    models.CharField(blank=True, db_index=True, max_length=255),
                ),
                ("type", models.CharField(db_index=True, max_length=30)),
                ("author_name", models.CharField(blank=True, max_length=255)),
                (
                    "author_platform_id",
                    models.CharField(blank=True, db_index=True, max_length=255),
                ),
                ("author_avatar", models.URLField(blank=True)),
                ("text", models.TextField(blank=True)),
                ("media_urls", models.JSONField(blank=True, default=list)),
                (
                    "post_id",
                    models.CharField(blank=True, db_index=True, max_length=255),
                ),
                ("thread_id", models.UUIDField(blank=True, db_index=True, null=True)),
                (
                    "sentiment",
                    models.CharField(blank=True, db_index=True, max_length=20),
                ),
                (
                    "sentiment_score",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=4, null=True
                    ),
                ),
                (
                    "spam_score",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=3, null=True
                    ),
                ),
                ("status", models.CharField(db_index=True, default="new", max_length=20)),
                ("assigned_to", models.CharField(blank=True, max_length=128)),
                ("assignment_reason", models.TextField(blank=True)),
                ("replied_at", models.DateTimeField(blank=True, null=True)),
                (
                    "response_time_minutes",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                ("received_at", models.DateTimeField(db_index=True)),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        help_text="Parent message for threaded replies",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="replies",
                        to="social_media.inboxmessage",
                    ),
                ),
            ],
            options={
                "db_table": "sm_inbox_messages",
                "ordering": ["-received_at"],
            },
        ),
        migrations.AddIndex(
            model_name="inboxmessage",
            index=models.Index(
                fields=["tenant_id", "received_at"], name="sm_inbox_tenant_recv"
            ),
        ),
        migrations.AddIndex(
            model_name="inboxmessage",
            index=models.Index(
                fields=["tenant_id", "status"], name="sm_inbox_tenant_status"
            ),
        ),
        migrations.AddIndex(
            model_name="inboxmessage",
            index=models.Index(
                fields=["tenant_id", "platform", "status"], name="sm_inbox_tenant_plat"
            ),
        ),
        migrations.AddIndex(
            model_name="inboxmessage",
            index=models.Index(
                fields=["assigned_to", "status"], name="sm_inbox_assigned"
            ),
        ),
        migrations.AddIndex(
            model_name="inboxmessage",
            index=models.Index(fields=["thread_id"], name="sm_inbox_thread"),
        ),
        migrations.AddIndex(
            model_name="inboxmessage",
            index=models.Index(
                fields=["tenant_id", "type", "status"], name="sm_inbox_tenant_type"
            ),
        ),
        migrations.CreateModel(
            name="SocialComment",
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
                ("platform", models.CharField(db_index=True, max_length=50)),
                (
                    "platform_comment_id",
                    models.CharField(blank=True, db_index=True, max_length=255),
                ),
                ("post_id", models.CharField(blank=True, db_index=True, max_length=255)),
                ("author_name", models.CharField(blank=True, max_length=255)),
                (
                    "author_platform_id",
                    models.CharField(blank=True, db_index=True, max_length=255),
                ),
                ("author_avatar", models.URLField(blank=True)),
                ("text", models.TextField(blank=True)),
                ("sentiment", models.CharField(blank=True, db_index=True, max_length=20)),
                (
                    "sentiment_score",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=4, null=True
                    ),
                ),
                (
                    "spam_score",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=3, null=True
                    ),
                ),
                ("spam_reasons", models.JSONField(blank=True, default=list)),
                ("is_spam", models.BooleanField(db_index=True, default=False)),
                ("is_hidden", models.BooleanField(db_index=True, default=False)),
                ("hidden_reason", models.TextField(blank=True)),
                (
                    "moderation_action",
                    models.CharField(db_index=True, default="none", max_length=20),
                ),
                ("moderated_by", models.CharField(blank=True, max_length=128)),
                ("moderated_at", models.DateTimeField(blank=True, null=True)),
                ("reply_text", models.TextField(blank=True)),
                ("replied_by", models.CharField(blank=True, max_length=128)),
                ("replied_at", models.DateTimeField(blank=True, null=True)),
                ("ai_suggestions", models.JSONField(blank=True, default=list)),
                ("like_count", models.PositiveIntegerField(default=0)),
                ("received_at", models.DateTimeField(db_index=True)),
                (
                    "parent_comment",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="replies",
                        to="social_media.socialcomment",
                    ),
                ),
            ],
            options={
                "db_table": "sm_social_comments",
                "ordering": ["-received_at"],
            },
        ),
        migrations.AddIndex(
            model_name="socialcomment",
            index=models.Index(
                fields=["tenant_id", "post_id", "received_at"],
                name="sm_comment_tpost_recv",
            ),
        ),
        migrations.AddIndex(
            model_name="socialcomment",
            index=models.Index(
                fields=["tenant_id", "is_spam"], name="sm_comment_tenant_spam"
            ),
        ),
        migrations.AddIndex(
            model_name="socialcomment",
            index=models.Index(
                fields=["tenant_id", "is_hidden"], name="sm_comment_tenant_hidden"
            ),
        ),
        migrations.AddIndex(
            model_name="socialcomment",
            index=models.Index(
                fields=["tenant_id", "platform", "received_at"],
                name="sm_comment_tenant_plat",
            ),
        ),
        migrations.AddIndex(
            model_name="socialcomment",
            index=models.Index(
                fields=["tenant_id", "sentiment", "spam_score"],
                name="sm_comment_sent_spam",
            ),
        ),
    ]
