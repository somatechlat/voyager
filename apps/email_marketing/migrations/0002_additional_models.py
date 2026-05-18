# Generated initial migration for email_marketing


from django.db import migrations, models


class PredictiveType(models.TextChoices):
    CHURN_RISK = "churn_risk", "Churn Risk"
    HIGH_LTV = "high_ltv", "High LTV"
    ENGAGEMENT_PROPENSITY = "engagement_propensity", "Engagement Propensity"
    NONE = "none", "None"


class Status(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    ARCHIVED = "archived", "Archived"


class TriggerType(models.TextChoices):
    LIST_SIGNUP = "list_signup", "List Signup"
    PURCHASE = "purchase", "Purchase"
    DATE = "date", "Date"
    BEHAVIOR = "behavior", "Behavior"
    API_EVENT = "api_event", "API Event"
    TAG_ADDED = "tag_added", "Tag Added"
    EMAIL_ACTION = "email_action", "Email Action"
    SCORE_CHANGE = "score_change", "Score Change"
    ABANDONED_CART = "abandoned_cart", "Abandoned Cart"
    PAGE_VISIT = "page_visit", "Page Visit"


class Type(models.TextChoices):
    STATIC = "static", "Static"
    DYNAMIC = "dynamic", "Dynamic"
    BEHAVIORAL = "behavioral", "Behavioral"
    PREDICTIVE = "predictive", "Predictive"


class Migration(migrations.Migration):

    initial = True

    dependencies = [("email_marketing", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="AutomationSequence",
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
                ("name", models.CharField(max_length=255, help_text="Sequence name")),
                (
                    "trigger_type",
                    models.CharField(
                        max_length=20,
                        choices=TriggerType.choices,
                        default=TriggerType.LIST_SIGNUP,
                        db_index=True,
                        help_text="What triggers the sequence",
                    ),
                ),
                (
                    "trigger_config",
                    models.JSONField(
                        default=dict,
                        help_text="Trigger configuration (listId, productId, etc.)",
                    ),
                ),
                ("steps", models.JSONField(default=list, help_text="JSON array of sequence steps")),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.DRAFT,
                        db_index=True,
                        help_text="Sequence lifecycle status",
                    ),
                ),
                (
                    "total_enrolled",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Total subscribers enrolled",
                    ),
                ),
                (
                    "total_completed",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Total subscribers who completed",
                    ),
                ),
                (
                    "total_exited",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Total subscribers who exited early",
                    ),
                ),
                (
                    "avg_completion_time_hours",
                    models.DecimalField(
                        max_digits=10,
                        decimal_places=2,
                        null=True,
                        blank=True,
                        help_text="Average time to complete in hours",
                    ),
                ),
                (
                    "entry_criteria",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Enrollment criteria",
                    ),
                ),
                (
                    "exit_criteria",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Early-exit criteria",
                    ),
                ),
                (
                    "frequency_cap",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Max times a subscriber can enter (0=unlimited)",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
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
                "db_table": "voyager_automation_sequence",
                "verbose_name": "Automation Sequence",
                "verbose_name_plural": "Automation Sequences",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "status"]),
                    models.Index(fields=["tenant_id", "trigger_type"]),
                    models.Index(fields=["tenant_id", "status", "trigger_type"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="AudienceSegment",
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
                ("name", models.CharField(max_length=255, help_text="Segment name")),
                (
                    "segment_type",
                    models.CharField(
                        max_length=20,
                        choices=Type.choices,
                        default=Type.STATIC,
                        db_index=True,
                        help_text="Segment type",
                    ),
                ),
                (
                    "rules",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="JSON segment rules definition",
                    ),
                ),
                (
                    "subscriber_count",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Cached subscriber count",
                    ),
                ),
                (
                    "last_calculated",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When the count was last refreshed",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Human-readable segment description",
                    ),
                ),
                (
                    "rfm_enabled",
                    models.BooleanField(
                        default=False,
                        help_text="Whether RFM scoring is used",
                    ),
                ),
                (
                    "rfm_config",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="RFM scoring configuration (recency, frequency, monetary thresholds)",
                    ),
                ),
                (
                    "predictive_type",
                    models.CharField(
                        max_length=30,
                        choices=PredictiveType.choices,
                        default=PredictiveType.NONE,
                        help_text="Predictive model type",
                    ),
                ),
                (
                    "is_system",
                    models.BooleanField(
                        default=False,
                        help_text="Whether this is a system segment",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
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
                "db_table": "voyager_audience_segment",
                "verbose_name": "Audience Segment",
                "verbose_name_plural": "Audience Segments",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "segment_type"]),
                    models.Index(fields=["tenant_id", "predictive_type"]),
                    models.Index(fields=["tenant_id", "is_system"]),
                ],
            },
        ),
    ]
