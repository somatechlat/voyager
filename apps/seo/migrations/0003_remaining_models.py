# Generated initial migration for seo

import uuid

from django.db import migrations, models


class AlertThreshold(models.TextChoices):
    NONE = "none", "No Alerts"
    SMALL = "small", "3+ Position Changes"
    MEDIUM = "medium", "5+ Position Changes"
    LARGE = "large", "10+ Position Changes"


class Device(models.TextChoices):
    DESKTOP = "desktop", "Desktop"
    MOBILE = "mobile", "Mobile"
    BOTH = "both", "Both"


class ReportFrequency(models.TextChoices):
    ONE_TIME = "one_time", "One Time"
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"
    QUARTERLY = "quarterly", "Quarterly"


class ReportType(models.TextChoices):
    EXECUTIVE = "executive", "Executive Summary"
    KEYWORD = "keyword", "Keyword Rankings"
    BACKLINK = "backlink", "Backlink Profile"
    TECHNICAL = "technical", "Technical Health"
    CONTENT = "content", "Content Score"
    COMPREHENSIVE = "comprehensive", "Comprehensive"


class Status(models.TextChoices):
    PENDING = "pending", "Pending"
    GENERATING = "generating", "Generating"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class Migration(migrations.Migration):

    initial = True

    dependencies = [("seo", "0002_additional_models")]

    operations = [
        migrations.CreateModel(
            name="SERPTracking",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=128, db_index=True)),
                (
                    "keyword",
                    models.ForeignKey(
                        to="seo.Keyword",
                        on_delete=models.CASCADE,
                        related_name="serp_tracking",
                        help_text="Tracked keyword",
                    ),
                ),
                (
                    "target_url",
                    models.URLField(
                        max_length=2048,
                        blank=True,
                        help_text="Expected ranking URL",
                    ),
                ),
                (
                    "locations_json",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="ISO country codes to track",
                    ),
                ),
                (
                    "device",
                    models.CharField(
                        max_length=16,
                        choices=Device.choices,
                        default=Device.BOTH,
                    ),
                ),
                (
                    "alert_threshold",
                    models.CharField(
                        max_length=16,
                        choices=AlertThreshold.choices,
                        default=AlertThreshold.MEDIUM,
                    ),
                ),
                ("is_active", models.BooleanField(default=True, db_index=True)),
                ("current_position", models.PositiveIntegerField(null=True, blank=True)),
                ("previous_position", models.PositiveIntegerField(null=True, blank=True)),
                ("position_change", models.IntegerField(default=0)),
                ("current_url", models.URLField(max_length=2048, blank=True)),
                (
                    "serp_features_json",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Detected SERP features",
                    ),
                ),
                ("last_checked_at", models.DateTimeField(null=True, blank=True)),
                ("check_count", models.PositiveIntegerField(default=0)),
                ("best_position", models.PositiveIntegerField(null=True, blank=True)),
                ("worst_position", models.PositiveIntegerField(null=True, blank=True)),
                ("metadata_json", models.JSONField(default=dict, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "voyager_serp_tracking",
                "verbose_name": "SERP Tracking",
                "verbose_name_plural": "SERP Trackings",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "keyword_id"]),
                    models.Index(fields=["tenant_id", "is_active"]),
                    models.Index(fields=["tenant_id", "-last_checked_at"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="RankHistory",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                (
                    "tracking",
                    models.ForeignKey(
                        SERPTracking,
                        on_delete=models.CASCADE,
                        related_name="history",
                        help_text="Parent tracking entry",
                    ),
                ),
                ("keyword_text", models.CharField(max_length=500, db_index=True)),
                ("position", models.PositiveIntegerField(null=True, blank=True)),
                ("previous_position", models.PositiveIntegerField(null=True, blank=True)),
                ("position_change", models.IntegerField(default=0)),
                ("url", models.URLField(max_length=2048, blank=True)),
                ("serp_features_json", models.JSONField(default=list, blank=True)),
                ("location", models.CharField(max_length=10, default="US")),
                ("device", models.CharField(max_length=16, default="desktop")),
                ("search_volume", models.PositiveIntegerField(null=True, blank=True)),
                (
                    "competitors_json",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Top 10 competitor URLs and positions",
                    ),
                ),
                ("page_title", models.TextField(blank=True)),
                ("page_description", models.TextField(blank=True)),
                ("tracked_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "db_table": "voyager_rank_history",
                "verbose_name": "Rank History",
                "verbose_name_plural": "Rank History",
                "ordering": ["-tracked_at"],
                "indexes": [
                    models.Index(fields=["tracking", "-tracked_at"]),
                    models.Index(fields=["keyword_text", "location", "device", "-tracked_at"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="SEOReport",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=128, db_index=True)),
                ("name", models.CharField(max_length=255, help_text="Report name")),
                (
                    "report_type",
                    models.CharField(
                        max_length=20,
                        choices=ReportType.choices,
                        default=ReportType.COMPREHENSIVE,
                    ),
                ),
                (
                    "frequency",
                    models.CharField(
                        max_length=16,
                        choices=ReportFrequency.choices,
                        default=ReportFrequency.MONTHLY,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=16,
                        choices=Status.choices,
                        default=Status.PENDING,
                        db_index=True,
                    ),
                ),
                (
                    "sections_json",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Enabled report sections",
                    ),
                ),
                ("date_from", models.DateField(help_text="Report period start")),
                ("date_to", models.DateField(help_text="Report period end")),
                ("brand_logo_url", models.URLField(max_length=2048, blank=True)),
                ("brand_primary_color", models.CharField(max_length=7, blank=True)),
                ("brand_name", models.CharField(max_length=255, blank=True)),
                ("custom_header", models.TextField(blank=True)),
                ("custom_footer", models.TextField(blank=True)),
                ("executive_summary_json", models.JSONField(default=dict, blank=True)),
                ("keyword_rankings_json", models.JSONField(default=dict, blank=True)),
                ("backlink_profile_json", models.JSONField(default=dict, blank=True)),
                ("technical_health_json", models.JSONField(default=dict, blank=True)),
                ("content_score_json", models.JSONField(default=dict, blank=True)),
                (
                    "report_file",
                    models.FileField(
                        upload_to="seo_reports/%Y/%m/",
                        blank=True,
                        help_text="Generated report file (PDF/HTML)",
                    ),
                ),
                (
                    "file_format",
                    models.CharField(
                        max_length=10,
                        default="pdf",
                        help_text="pdf or html",
                    ),
                ),
                (
                    "compare_with_previous",
                    models.BooleanField(
                        default=True,
                        help_text="Compare with previous period",
                    ),
                ),
                ("previous_period_json", models.JSONField(default=dict, blank=True)),
                ("is_scheduled", models.BooleanField(default=False, db_index=True)),
                ("next_run_at", models.DateTimeField(null=True, blank=True, db_index=True)),
                (
                    "recipients_json",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Email addresses for report delivery",
                    ),
                ),
                ("error_message", models.TextField(blank=True)),
                ("metadata_json", models.JSONField(default=dict, blank=True)),
                ("generated_at", models.DateTimeField(null=True, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "voyager_seo_report",
                "verbose_name": "SEO Report",
                "verbose_name_plural": "SEO Reports",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "report_type"]),
                    models.Index(fields=["tenant_id", "status"]),
                    models.Index(fields=["tenant_id", "is_scheduled"]),
                    models.Index(fields=["tenant_id", "-created_at"]),
                ],
            },
        ),
    ]
