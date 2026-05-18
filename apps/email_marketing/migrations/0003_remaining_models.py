# Generated initial migration for email_marketing


from django.db import migrations, models


class DmarcPolicy(models.TextChoices):
    NONE = "none", "None"
    QUARANTINE = "quarantine", "Quarantine"
    REJECT = "reject", "Reject"
    UNKNOWN = "unknown", "Unknown"


class Grade(models.TextChoices):
    A = "A", "A"
    B = "B", "B"
    C = "C", "C"
    D = "D", "D"
    F = "F", "F"


class Status(models.TextChoices):
    DRAFT = "draft", "Draft"
    SCHEDULED = "scheduled", "Scheduled"
    RUNNING = "running", "Running"
    WINNER_SELECTED = "winner_selected", "Winner Selected"
    DEPLOYED = "deployed", "Deployed"
    PAUSED = "paused", "Paused"
    CANCELLED = "cancelled", "Cancelled"


class TestType(models.TextChoices):
    SUBJECT = "subject", "Subject Line"
    CONTENT = "content", "Email Content"
    SENDER = "sender", "Sender Name"
    SEND_TIME = "send_time", "Send Time"
    MULTI = "multi", "Multi-variant"


class WinningMetric(models.TextChoices):
    OPENS = "opens", "Open Rate"
    CLICKS = "clicks", "Click Rate"
    CTR = "ctr", "Click-Through Rate"
    REVENUE = "revenue", "Revenue"
    CONVERSIONS = "conversions", "Conversions"


class Migration(migrations.Migration):

    initial = True

    dependencies = [("email_marketing", "0002_additional_models")]

    operations = [
        migrations.CreateModel(
            name="DeliverabilityMonitor",
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
                    "domain",
                    models.CharField(
                        max_length=255,
                        db_index=True,
                        help_text="Sending domain being monitored",
                    ),
                ),
                (
                    "spf_configured",
                    models.BooleanField(
                        default=False,
                        help_text="Whether SPF record is present",
                    ),
                ),
                (
                    "spf_valid",
                    models.BooleanField(
                        default=False,
                        help_text="Whether SPF record is valid",
                    ),
                ),
                (
                    "spf_includes",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="SPF include mechanisms",
                    ),
                ),
                (
                    "dkim_configured",
                    models.BooleanField(
                        default=False,
                        help_text="Whether DKIM record is present",
                    ),
                ),
                (
                    "dkim_valid",
                    models.BooleanField(
                        default=False,
                        help_text="Whether DKIM record is valid",
                    ),
                ),
                (
                    "dkim_selector",
                    models.CharField(
                        max_length=50,
                        blank=True,
                        default="default",
                        help_text="DKIM selector used",
                    ),
                ),
                (
                    "dmarc_configured",
                    models.BooleanField(
                        default=False,
                        help_text="Whether DMARC record is present",
                    ),
                ),
                (
                    "dmarc_policy",
                    models.CharField(
                        max_length=20,
                        choices=DmarcPolicy.choices,
                        default=DmarcPolicy.UNKNOWN,
                        help_text="DMARC policy",
                    ),
                ),
                ("dmarc_rua", models.URLField(blank=True, help_text="DMARC aggregate report URI")),
                ("dmarc_ruf", models.URLField(blank=True, help_text="DMARC forensic report URI")),
                (
                    "bimi_configured",
                    models.BooleanField(
                        default=False,
                        help_text="Whether BIMI record is present",
                    ),
                ),
                ("bimi_logo_url", models.URLField(blank=True, help_text="BIMI logo URL")),
                (
                    "reputation_score",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        default=0.0,
                        help_text="Overall sender reputation score (0-100)",
                    ),
                ),
                (
                    "reputation_grade",
                    models.CharField(
                        max_length=1,
                        choices=Grade.choices,
                        default=Grade.F,
                        help_text="Letter grade",
                    ),
                ),
                (
                    "bounce_rate",
                    models.DecimalField(
                        max_digits=6,
                        decimal_places=4,
                        default=0.0,
                        help_text="Current bounce rate",
                    ),
                ),
                (
                    "spam_complaint_rate",
                    models.DecimalField(
                        max_digits=7,
                        decimal_places=6,
                        default=0.0,
                        help_text="Current spam complaint rate",
                    ),
                ),
                (
                    "blacklist_status",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Blacklist check results",
                    ),
                ),
                (
                    "volume_24h",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Emails sent in last 24 hours",
                    ),
                ),
                (
                    "volume_7d",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Emails sent in last 7 days",
                    ),
                ),
                (
                    "volume_30d",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Emails sent in last 30 days",
                    ),
                ),
                (
                    "inbox_placement_pct",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                        help_text="Inbox placement rate",
                    ),
                ),
                (
                    "checked_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="Last check timestamp",
                    ),
                ),
                (
                    "recommendations",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Improvement recommendations",
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
                "db_table": "voyager_deliverability_monitor",
                "verbose_name": "Deliverability Monitor",
                "verbose_name_plural": "Deliverability Monitors",
                "ordering": ["-checked_at", "-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "domain"]),
                    models.Index(fields=["tenant_id", "reputation_score"]),
                    models.Index(fields=["tenant_id", "checked_at"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="EmailABTest",
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
                ("name", models.CharField(max_length=255, help_text="Test name")),
                (
                    "test_type",
                    models.CharField(
                        max_length=20,
                        choices=TestType.choices,
                        default=TestType.SUBJECT,
                        db_index=True,
                        help_text="What element is being tested",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.DRAFT,
                        db_index=True,
                        help_text="Test lifecycle status",
                    ),
                ),
                (
                    "campaign_name",
                    models.CharField(
                        max_length=255,
                        blank=True,
                        help_text="Name for the winning campaign",
                    ),
                ),
                (
                    "sample_size",
                    models.PositiveIntegerField(
                        null=True,
                        blank=True,
                        help_text="Number of subscribers per variant",
                    ),
                ),
                (
                    "sample_pct",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        default=20.0,
                        help_text="Percentage of list to test before winner",
                    ),
                ),
                (
                    "confidence_level",
                    models.DecimalField(
                        max_digits=4,
                        decimal_places=3,
                        default=0.95,
                        help_text="Statistical confidence level",
                    ),
                ),
                (
                    "winning_metric",
                    models.CharField(
                        max_length=20,
                        choices=WinningMetric.choices,
                        default=WinningMetric.OPENS,
                        help_text="Metric used to pick winner",
                    ),
                ),
                (
                    "winner_variant_id",
                    models.CharField(
                        max_length=64,
                        blank=True,
                        help_text="ID of the winning variant",
                    ),
                ),
                (
                    "winner_selected_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When winner was determined",
                    ),
                ),
                (
                    "auto_deploy",
                    models.BooleanField(
                        default=True,
                        help_text="Auto-send winner to remaining list",
                    ),
                ),
                (
                    "total_sent",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Total emails sent across all variants",
                    ),
                ),
                (
                    "total_conversions",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Total conversions across all variants",
                    ),
                ),
                (
                    "variants",
                    models.JSONField(
                        default=list,
                        help_text="Variant definitions (subject lines, content, etc.)",
                    ),
                ),
                (
                    "results",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Per-variant performance results",
                    ),
                ),
                (
                    "segment_id_ref",
                    models.CharField(
                        max_length=128,
                        blank=True,
                        help_text="Target audience segment reference",
                    ),
                ),
                (
                    "scheduled_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When the test should start",
                    ),
                ),
                (
                    "started_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When the test actually started",
                    ),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When the test completed",
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
                "db_table": "voyager_email_ab_test",
                "verbose_name": "Email A/B Test",
                "verbose_name_plural": "Email A/B Tests",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "status"]),
                    models.Index(fields=["tenant_id", "test_type"]),
                    models.Index(fields=["tenant_id", "scheduled_at"]),
                ],
            },
        ),
    ]
