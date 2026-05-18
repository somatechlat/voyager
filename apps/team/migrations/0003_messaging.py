"""Add MessageChannel and Message models."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Add MessageChannel and Message models."""

    dependencies = [('team', '0002_task_comments')]

    operations = [
            name="MessageChannel",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        max_length=128,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=255,
                        help_text="Channel display name",
                    ),
                ),
                (
                    "channel_type",
                    models.CharField(
                        choices=[
                            ("direct", "Direct"),
                            ("group", "Group"),
                        ],
                        db_index=True,
                        default="group",
                        max_length=20,
                        help_text="Direct (1:1) or group conversation",
                    ),
                ),
                (
                    "participant_ids",
                    models.JSONField(
                        default=list,
                        help_text="List of participant user IDs",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Timestamp when last updated",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_message_channel",
                "verbose_name": "Message Channel",
                "verbose_name_plural": "Message Channels",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.AddIndex(
            model_name="messagechannel",
            index=models.Index(
                fields=["tenant_id", "channel_type"],
                name="voyager_channel_tenant_type_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="messagechannel",
            index=models.Index(
                fields=["tenant_id", "-updated_at"],
                name="voyager_channel_tenant_updated_idx",
            ),
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "author_id",
                    models.CharField(
                        db_index=True,
                        max_length=128,
                        help_text="UUID of the message author",
                    ),
                ),
                (
                    "content",
                    models.TextField(
                        help_text="Message text content",
                    ),
                ),
                (
                    "mentions",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="List of mentioned user IDs",
                    ),
                ),
                (
                    "attachments",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="List of attachment file references",
                    ),
                ),
                (
                    "thread_parent_id",
                    models.BigIntegerField(
                        blank=True,
                        db_index=True,
                        null=True,
                        help_text="ID of parent message for threading",
                    ),
                ),
                (
                    "edited_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        help_text="Timestamp of last edit",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when created",
                    ),
                ),
                (
                    "channel",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="team.messagechannel",
                        help_text="Parent channel",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_message",
                "verbose_name": "Message",
                "verbose_name_plural": "Messages",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(
                fields=["channel", "-created_at"],
                name="voyager_message_channel_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(
                fields=["thread_parent_id", "-created_at"],
                name="voyager_message_thread_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(
                fields=["author_id", "-created_at"],
                name="voyager_message_author_created_idx",
            ),
        ),
        migrations.CreateModel(
    ]
