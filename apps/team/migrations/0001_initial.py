# Generated initial migration for team


from django.db import migrations, models


class Priority(models.TextChoices):
    P0 = "P0", "Critical"
    P1 = "P1", "High"
    P2 = "P2", "Medium"
    P3 = "P3", "Low"


class Status(models.TextChoices):
    TODO = "todo", "To Do"
    IN_PROGRESS = "in_progress", "In Progress"
    DONE = "done", "Done"
    CANCELLED = "cancelled", "Cancelled"


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Task",
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
                ("title", models.CharField(max_length=500, help_text="Short task title")),
                (
                    "description",
                    models.TextField(blank=True, help_text="Detailed task description"),
                ),
                (
                    "project_id",
                    models.CharField(
                        max_length=128,
                        blank=True,
                        db_index=True,
                        help_text="Optional linked project UUID",
                    ),
                ),
                (
                    "client_id",
                    models.CharField(
                        max_length=128,
                        blank=True,
                        db_index=True,
                        help_text="Optional linked client UUID",
                    ),
                ),
                (
                    "campaign_id",
                    models.CharField(
                        max_length=128,
                        blank=True,
                        db_index=True,
                        help_text="Optional linked campaign UUID",
                    ),
                ),
                (
                    "assignee_id",
                    models.CharField(
                        max_length=128,
                        blank=True,
                        db_index=True,
                        help_text="UUID of the assigned user",
                    ),
                ),
                (
                    "reporter_id",
                    models.CharField(
                        max_length=128,
                        blank=True,
                        db_index=True,
                        help_text="UUID of the user who created the task",
                    ),
                ),
                (
                    "priority",
                    models.CharField(
                        max_length=5,
                        choices=Priority.choices,
                        default=Priority.P2,
                        db_index=True,
                        help_text="Priority level P0-P3",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=30,
                        choices=Status.choices,
                        default=Status.TODO,
                        db_index=True,
                        help_text="Current task status",
                    ),
                ),
                (
                    "task_type",
                    models.CharField(
                        max_length=50,
                        blank=True,
                        db_index=True,
                        help_text="Type of work (design, development, etc.)",
                    ),
                ),
                (
                    "tags",
                    models.JSONField(default=list, blank=True, help_text="List of string tags"),
                ),
                (
                    "due_date",
                    models.DateField(
                        null=True,
                        blank=True,
                        db_index=True,
                        help_text="Deadline date",
                    ),
                ),
                (
                    "estimated_hours",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                        help_text="Estimated effort in hours",
                    ),
                ),
                (
                    "actual_hours",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                        help_text="Logged effort in hours",
                    ),
                ),
                (
                    "dependencies",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="List of dependent task IDs",
                    ),
                ),
                (
                    "subtasks",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="List of subtask objects with id, title, done fields",
                    ),
                ),
                (
                    "custom_fields",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Key-value custom fields",
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
                    "position",
                    models.IntegerField(
                        default=0,
                        help_text="Sort position for Kanban boards",
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
                        db_index=True,
                        help_text="Timestamp when last updated",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_task",
                "verbose_name": "Task",
                "verbose_name_plural": "Tasks",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "status", "priority"]),
                    models.Index(fields=["tenant_id", "assignee_id", "status"]),
                    models.Index(fields=["tenant_id", "project_id", "status"]),
                    models.Index(fields=["tenant_id", "due_date"]),
                    models.Index(fields=["tenant_id", "task_type"]),
                    models.Index(fields=["assignee_id", "due_date"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="TaskComment",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "task",
                    models.ForeignKey(
                        Task,
                        on_delete=models.CASCADE,
                        related_name="comments",
                        help_text="Parent task",
                    ),
                ),
                (
                    "author_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="UUID of the comment author",
                    ),
                ),
                ("content", models.TextField(help_text="Comment text content")),
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
                        help_text="List of attachment references",
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
                "db_table": "voyager_task_comment",
                "verbose_name": "Task Comment",
                "verbose_name_plural": "Task Comments",
                "ordering": ["created_at"],
                "indexes": [
                    models.Index(fields=["task", "created_at"]),
                    models.Index(fields=["author_id", "created_at"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="TaskTimeEntry",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "task",
                    models.ForeignKey(
                        Task,
                        on_delete=models.CASCADE,
                        related_name="time_entries",
                        help_text="Parent task",
                    ),
                ),
                (
                    "user_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="UUID of the user who logged time",
                    ),
                ),
                ("started_at", models.DateTimeField(db_index=True, help_text="When work began")),
                (
                    "ended_at",
                    models.DateTimeField(null=True, blank=True, help_text="When work ended"),
                ),
                (
                    "duration_seconds",
                    models.IntegerField(
                        null=True,
                        blank=True,
                        help_text="Computed duration in seconds",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Optional description of work performed",
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
                "db_table": "voyager_task_time_entry",
                "verbose_name": "Task Time Entry",
                "verbose_name_plural": "Task Time Entries",
                "ordering": ["-started_at"],
                "indexes": [
                    models.Index(fields=["task", "user_id"]),
                    models.Index(fields=["user_id", "started_at"]),
                    models.Index(fields=["task", "started_at"]),
                ],
            },
        ),
    ]
