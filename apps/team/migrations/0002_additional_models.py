# Generated initial migration for team


from django.db import migrations, models


class ChannelType(models.TextChoices):
    DIRECT = "direct", "Direct"
    GROUP = "group", "Group"


class Migration(migrations.Migration):

    initial = True

    dependencies = [("team", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="MessageChannel",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                ("name", models.CharField(max_length=255, help_text="Channel display name")),
                (
                    "channel_type",
                    models.CharField(
                        max_length=20,
                        choices=ChannelType.choices,
                        default=ChannelType.GROUP,
                        db_index=True,
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
                "indexes": [
                    models.Index(fields=["tenant_id", "channel_type"]),
                    models.Index(fields=["tenant_id", "-updated_at"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "channel",
                    models.ForeignKey(
                        MessageChannel,
                        on_delete=models.CASCADE,
                        related_name="messages",
                        help_text="Parent channel",
                    ),
                ),
                (
                    "author_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="UUID of the message author",
                    ),
                ),
                ("content", models.TextField(help_text="Message text content")),
                (
                    "mentions",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="List of mentioned user IDs",
                    ),
                ),
                (
                    "attachments",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="List of attachment file references",
                    ),
                ),
                (
                    "thread_parent_id",
                    models.BigIntegerField(
                        null=True,
                        blank=True,
                        db_index=True,
                        help_text="ID of parent message for threading",
                    ),
                ),
                (
                    "edited_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
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
            ],
            options={
                "db_table": "voyager_message",
                "verbose_name": "Message",
                "verbose_name_plural": "Messages",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["channel", "-created_at"]),
                    models.Index(fields=["thread_parent_id", "-created_at"]),
                    models.Index(fields=["author_id", "-created_at"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="ActivityFeed",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "actor_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="UUID of the user who performed the action",
                    ),
                ),
                (
                    "action_type",
                    models.CharField(
                        max_length=50,
                        db_index=True,
                        help_text="Type of action (e.g. task.created, task.assigned)",
                    ),
                ),
                (
                    "target_type",
                    models.CharField(
                        max_length=50,
                        blank=True,
                        db_index=True,
                        help_text="Type of resource affected (e.g. task, message)",
                    ),
                ),
                (
                    "target_id",
                    models.CharField(
                        max_length=128,
                        blank=True,
                        db_index=True,
                        help_text="ID of the affected resource",
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Additional context as key-value pairs",
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
            ],
            options={
                "db_table": "voyager_activity_feed",
                "verbose_name": "Activity Feed Entry",
                "verbose_name_plural": "Activity Feed Entries",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "-created_at"]),
                    models.Index(fields=["tenant_id", "actor_id", "-created_at"]),
                    models.Index(fields=["tenant_id", "action_type", "-created_at"]),
                    models.Index(fields=["target_type", "target_id"]),
                ],
            },
        ),
    ]
