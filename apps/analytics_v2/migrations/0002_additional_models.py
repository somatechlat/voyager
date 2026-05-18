# Generated initial migration for analytics_v2

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [("analytics_v2", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="ReportTemplate",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=64, db_index=True)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                (
                    "category",
                    models.CharField(
                        max_length=64,
                        default="general",
                        db_index=True,
                        help_text="Report category: engagement, reach, conversion, seo, email, etc.",
                    ),
                ),
                (
                    "config",
                    models.JSONField(
                        default=dict,
                        help_text="Metrics, dimensions, filters, visualizations, sorting",
                    ),
                ),
                (
                    "format",
                    models.CharField(
                        max_length=16,
                        choices=REPORT_FORMAT_CHOICES,
                        default="pdf",
                    ),
                ),
                ("is_favorite", models.BooleanField(default=False)),
                ("created_by", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={
                "db_table": "analytics_report_template",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "category"]),
                    models.Index(fields=["tenant_id", "-created_at"]),
                    models.Index(fields=["tenant_id", "is_favorite"]),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["tenant_id", "name"], name="%(app_label)s_rpt_tenant_name_uniq"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="ReportSchedule",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=64, db_index=True)),
                (
                    "template",
                    models.ForeignKey(
                        ReportTemplate,
                        on_delete=models.CASCADE,
                        related_name="schedules",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                (
                    "frequency",
                    models.CharField(
                        max_length=16,
                        choices=SCHEDULE_FREQUENCY_CHOICES,
                        default="weekly",
                    ),
                ),
                (
                    "cron_expression",
                    models.CharField(
                        max_length=128,
                        blank=True,
                        help_text="Optional cron for advanced scheduling",
                    ),
                ),
                ("next_run_at", models.DateTimeField(null=True, blank=True, db_index=True)),
                ("last_run_at", models.DateTimeField(null=True, blank=True)),
                (
                    "last_run_status",
                    models.CharField(
                        max_length=16,
                        choices=REPORT_STATUS_CHOICES,
                        default="draft",
                    ),
                ),
                ("last_run_result", models.JSONField(default=dict, blank=True)),
                (
                    "delivery",
                    models.JSONField(
                        default=dict,
                        help_text="Delivery channels: email, slack, webhook, s3",
                    ),
                ),
                ("timezone", models.CharField(max_length=64, default="UTC")),
                ("is_active", models.BooleanField(default=True)),
                ("created_by", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={
                "db_table": "analytics_report_schedule",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "is_active", "next_run_at"]),
                    models.Index(fields=["tenant_id", "-created_at"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="AttributionModel",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=64, db_index=True)),
                ("name", models.CharField(max_length=255)),
                (
                    "model_type",
                    models.CharField(
                        max_length=32,
                        choices=ATTRIBUTION_MODEL_CHOICES,
                        default="last_touch",
                    ),
                ),
                (
                    "config",
                    models.JSONField(
                        default=dict,
                        help_text="Model-specific parameters: half_life, first_weight, last_weight",
                    ),
                ),
                ("lookback_window_days", models.PositiveIntegerField(default=30)),
                ("is_default", models.BooleanField(default=False)),
                ("created_by", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={
                "db_table": "analytics_attribution_model",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "model_type"]),
                    models.Index(fields=["tenant_id", "is_default"]),
                    models.Index(fields=["tenant_id", "-created_at"]),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["tenant_id", "name"], name="%(app_label)s_attr_tenant_name_uniq"
                    )
                ],
            },
        ),
    ]
