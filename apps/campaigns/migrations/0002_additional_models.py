# Generated initial migration for campaigns


from django.db import migrations, models


class EntryType(models.TextChoices):
    ALLOCATION = "allocation", "Allocation"
    SPEND = "spend", "Spend"
    ADJUSTMENT = "adjustment", "Adjustment"
    REFUND = "refund", "Refund"


class Method(models.TextChoices):
    FREQUENTIST = "frequentist", "Frequentist"
    BAYESIAN = "bayesian", "Bayesian"


class Status(models.TextChoices):
    DRAFT = "draft", "Draft"
    RUNNING = "running", "Running"
    PAUSED = "paused", "Paused"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class TestType(models.TextChoices):
    SUBJECT_LINE = "subject_line", "Subject Line"
    CREATIVE = "creative", "Creative"
    LANDING_PAGE = "landing_page", "Landing Page"
    AUDIENCE = "audience", "Audience"
    BID_STRATEGY = "bid_strategy", "Bid Strategy"
    AD_COPY = "ad_copy", "Ad Copy"
    CTA = "cta", "Call to Action"
    PLACEMENT = "placement", "Placement"


class WinnerCriteria(models.TextChoices):
    CONVERSION_RATE = "conversion_rate", "Conversion Rate"
    CLICK_RATE = "click_rate", "Click Rate"
    REVENUE = "revenue", "Revenue"
    ROAS = "roas", "ROAS"
    CPA = "cpa", "CPA"
    ENGAGEMENT = "engagement", "Engagement"


class Migration(migrations.Migration):

    initial = True

    dependencies = [("campaigns", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="CampaignABTest",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "campaign",
                    models.ForeignKey(
                        Campaign,
                        on_delete=models.CASCADE,
                        related_name="ab_tests",
                        help_text="Parent campaign",
                    ),
                ),
                ("name", models.CharField(max_length=255, help_text="Test name")),
                (
                    "test_type",
                    models.CharField(
                        max_length=30,
                        choices=TestType.choices,
                        db_index=True,
                        help_text="Type of element being tested",
                    ),
                ),
                (
                    "method",
                    models.CharField(
                        max_length=15,
                        choices=Method.choices,
                        default=Method.FREQUENTIST,
                        help_text="Statistical method",
                    ),
                ),
                (
                    "significance_level",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=4,
                        default=0.05,
                        help_text="Alpha level (e.g. 0.05)",
                    ),
                ),
                (
                    "power",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=4,
                        default=0.8,
                        help_text="Statistical power (e.g. 0.80)",
                    ),
                ),
                (
                    "sample_size_per_variant",
                    models.PositiveIntegerField(
                        null=True,
                        blank=True,
                        help_text="Required sample size per variant",
                    ),
                ),
                (
                    "actual_sample_size",
                    models.PositiveIntegerField(
                        null=True,
                        blank=True,
                        help_text="Actual sample size reached",
                    ),
                ),
                (
                    "baseline_rate",
                    models.DecimalField(
                        max_digits=7,
                        decimal_places=5,
                        null=True,
                        blank=True,
                        help_text="Baseline conversion rate (e.g. 0.05)",
                    ),
                ),
                (
                    "minimum_detectable_effect",
                    models.DecimalField(
                        max_digits=6,
                        decimal_places=4,
                        null=True,
                        blank=True,
                        help_text="Relative lift to detect (e.g. 0.20)",
                    ),
                ),
                (
                    "daily_traffic",
                    models.PositiveIntegerField(
                        null=True,
                        blank=True,
                        help_text="Expected daily visitors",
                    ),
                ),
                (
                    "estimated_duration_days",
                    models.PositiveIntegerField(
                        null=True,
                        blank=True,
                        help_text="Calculated test duration in days",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=15,
                        choices=Status.choices,
                        default=Status.DRAFT,
                        db_index=True,
                        help_text="Test lifecycle status",
                    ),
                ),
                (
                    "winner_criteria",
                    models.CharField(
                        max_length=20,
                        choices=WinnerCriteria.choices,
                        default=WinnerCriteria.CONVERSION_RATE,
                        help_text="Metric for selecting winner",
                    ),
                ),
                (
                    "winner_variant_id",
                    models.CharField(
                        max_length=128,
                        blank=True,
                        help_text="ID of winning variant",
                    ),
                ),
                (
                    "variants",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Array of test variants with id, name, traffic_split",
                    ),
                ),
                (
                    "results",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Test results (z-statistic, p-value, credible intervals)",
                    ),
                ),
                (
                    "start_date",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When the test started",
                    ),
                ),
                (
                    "end_date",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When the test ended",
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
                "db_table": "voyager_campaign_ab_test",
                "verbose_name": "Campaign A/B Test",
                "verbose_name_plural": "Campaign A/B Tests",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["campaign", "status"]),
                    models.Index(fields=["campaign", "test_type"]),
                    models.Index(fields=["method", "status"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="CampaignBudget",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "campaign",
                    models.ForeignKey(
                        Campaign,
                        on_delete=models.CASCADE,
                        related_name="budget_entries",
                        help_text="Parent campaign",
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=2,
                        help_text="Transaction amount (positive allocation, negative spend)",
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        max_length=20,
                        choices=EntryType.choices,
                        db_index=True,
                        help_text="Type of budget entry",
                    ),
                ),
                (
                    "channel",
                    models.CharField(
                        max_length=50,
                        blank=True,
                        db_index=True,
                        help_text="Channel reference (e.g. 'google_ads')",
                    ),
                ),
                (
                    "description",
                    models.TextField(blank=True, help_text="Human-readable description"),
                ),
                (
                    "metadata",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Additional context (roas, cpa, impressions, etc)",
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
                "db_table": "voyager_campaign_budget",
                "verbose_name": "Campaign Budget Entry",
                "verbose_name_plural": "Campaign Budget Entries",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["campaign", "type", "-created_at"]),
                    models.Index(fields=["campaign", "channel", "-created_at"]),
                    models.Index(fields=["campaign", "-created_at"]),
                ],
            },
        ),
    ]
