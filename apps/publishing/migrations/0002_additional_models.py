# Generated initial migration for publishing


from django.db import migrations, models


class RecurringType(models.TextChoices):
    NONE = "none", "Does not repeat"
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"


class VariationStrategy(models.TextChoices):
    ROUND_ROBIN = "round_robin", "Round Robin"
    RANDOM = "random", "Random"
    PERFORMANCE = "performance", "Performance"
    AI_ADAPT = "ai_adapt", "AI Adapt"


class WorkflowType(models.TextChoices):
    SEQUENTIAL = "sequential", "Sequential"
    PARALLEL = "parallel", "Parallel"
    CONDITIONAL = "conditional", "Conditional"


class Migration(migrations.Migration):

    initial = True

    dependencies = [("publishing", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="BlackoutWindow",
            fields=[
                ("name", models.CharField(max_length=255, help_text="Blackout name")),
                (
                    "account_id",
                    models.UUIDField(
                        null=True,
                        blank=True,
                        db_index=True,
                        help_text="Account scope; null = all accounts",
                    ),
                ),
                (
                    "platform",
                    models.CharField(
                        max_length=32,
                        blank=True,
                        db_index=True,
                        help_text="Platform scope; blank = all platforms",
                    ),
                ),
                ("start_at", models.DateTimeField(help_text="Blackout start")),
                ("end_at", models.DateTimeField(help_text="Blackout end")),
                (
                    "recurring",
                    models.CharField(
                        max_length=16,
                        choices=RecurringType.choices,
                        default=RecurringType.NONE,
                    ),
                ),
                ("is_active", models.BooleanField(default=True, db_index=True)),
                (
                    "metadata_json",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Additional blackout metadata",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_blackout_window",
                "verbose_name": "Blackout Window",
                "verbose_name_plural": "Blackout Windows",
                "ordering": ["-start_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "account_id", "platform"]),
                    models.Index(fields=["tenant_id", "start_at", "end_at"]),
                    models.Index(fields=["is_active", "start_at"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="RecurringPost",
            fields=[
                ("name", models.CharField(max_length=512, help_text="Series name")),
                ("platform", models.CharField(max_length=32, help_text="Target platform")),
                (
                    "account_id",
                    models.UUIDField(db_index=True, help_text="Platform connection UUID"),
                ),
                (
                    "publish_type",
                    models.CharField(
                        max_length=32,
                        default="feed",
                        help_text="Post type",
                    ),
                ),
                (
                    "cron_expression",
                    models.CharField(
                        max_length=128,
                        help_text="Cron expression for scheduling",
                    ),
                ),
                ("start_date", models.DateTimeField(help_text="Series start date")),
                (
                    "end_date",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="Optional series end",
                    ),
                ),
                (
                    "timezone",
                    models.CharField(
                        max_length=100,
                        default="UTC",
                        help_text="IANA timezone",
                    ),
                ),
                (
                    "content_pool",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="List of content variations",
                    ),
                ),
                (
                    "variation_strategy",
                    models.CharField(
                        max_length=32,
                        choices=VariationStrategy.choices,
                        default=VariationStrategy.ROUND_ROBIN,
                    ),
                ),
                (
                    "base_content",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Base content template: {caption, hashtags, media_urls, link, alt_text}",
                    ),
                ),
                (
                    "context_json",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Extra context for AI adaptation",
                    ),
                ),
                (
                    "last_instance_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="Last generated instance timestamp",
                    ),
                ),
                (
                    "last_instance_number",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Last generated instance number",
                    ),
                ),
                ("is_active", models.BooleanField(default=True, db_index=True)),
                (
                    "created_by",
                    models.CharField(max_length=256, db_index=True, help_text="User UUID"),
                ),
            ],
            options={
                "db_table": "voyager_recurring_post",
                "verbose_name": "Recurring Post",
                "verbose_name_plural": "Recurring Posts",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "is_active"]),
                    models.Index(fields=["tenant_id", "platform", "account_id"]),
                    models.Index(fields=["is_active", "start_date"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="ApprovalWorkflow",
            fields=[
                ("name", models.CharField(max_length=255, help_text="Workflow name")),
                (
                    "type",
                    models.CharField(
                        max_length=16,
                        choices=WorkflowType.choices,
                        help_text="Approval type",
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
                ("is_active", models.BooleanField(default=True, db_index=True)),
                (
                    "created_by",
                    models.CharField(max_length=256, db_index=True, help_text="User UUID"),
                ),
            ],
            options={
                "db_table": "voyager_approval_workflow",
                "verbose_name": "Approval Workflow",
                "verbose_name_plural": "Approval Workflows",
                "ordering": ["-created_at"],
            },
        ),
    ]
