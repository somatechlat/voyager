# Generated initial migration for analytics_v2

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [("analytics_v2", "0002_additional_models")]

    operations = [
        migrations.CreateModel(
            name="ConversionPath",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=64, db_index=True)),
                ("conversion_id", models.CharField(max_length=255, db_index=True)),
                ("user_id", models.CharField(max_length=255, blank=True, db_index=True)),
                (
                    "conversion_value",
                    models.DecimalField(max_digits=15, decimal_places=4, default=0),
                ),
                ("conversion_date", models.DateTimeField(db_index=True)),
                ("currency", models.CharField(max_length=3, default="USD")),
                ("channel", models.CharField(max_length=64, blank=True, db_index=True)),
                ("campaign", models.CharField(max_length=255, blank=True)),
                (
                    "attribution_model",
                    models.ForeignKey(
                        AttributionModel,
                        on_delete=models.SET_NULL,
                        null=True,
                        blank=True,
                        related_name="conversion_paths",
                    ),
                ),
                ("total_touchpoints", models.PositiveIntegerField(default=0)),
                (
                    "time_to_conversion_hours",
                    models.DecimalField(
                        max_digits=10,
                        decimal_places=2,
                        default=0,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "db_table": "analytics_conversion_path",
                "ordering": ["-conversion_date"],
                "indexes": [
                    models.Index(fields=["tenant_id", "conversion_date"]),
                    models.Index(fields=["tenant_id", "user_id"]),
                    models.Index(fields=["tenant_id", "channel"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="Touchpoint",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                (
                    "conversion",
                    models.ForeignKey(
                        ConversionPath,
                        on_delete=models.CASCADE,
                        related_name="touchpoints",
                    ),
                ),
                (
                    "sequence_order",
                    models.PositiveIntegerField(
                        default=1,
                        help_text="Position in the conversion journey (1 = first)",
                    ),
                ),
                (
                    "touchpoint_type",
                    models.CharField(
                        max_length=32,
                        choices=TOUCHPOINT_TYPE_CHOICES,
                        default="click",
                    ),
                ),
                ("channel", models.CharField(max_length=64, blank=True, db_index=True)),
                ("platform", models.CharField(max_length=64, blank=True, db_index=True)),
                ("campaign", models.CharField(max_length=255, blank=True)),
                ("ad_group", models.CharField(max_length=255, blank=True)),
                ("creative", models.CharField(max_length=255, blank=True)),
                ("landing_page", models.URLField(blank=True)),
                ("referrer", models.URLField(blank=True)),
                ("device_type", models.CharField(max_length=32, blank=True)),
                ("geographic", models.JSONField(default=dict, blank=True)),
                ("timestamp", models.DateTimeField(db_index=True)),
                (
                    "credit",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=4,
                        default=0,
                        help_text="Attribution credit (0.0 - 1.0)",
                    ),
                ),
                (
                    "revenue_attributed",
                    models.DecimalField(max_digits=15, decimal_places=4, default=0),
                ),
                (
                    "time_since_previous_hours",
                    models.DecimalField(
                        max_digits=10,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
            ],
            options={
                "db_table": "analytics_touchpoint",
                "ordering": ["conversion", "sequence_order"],
                "indexes": [
                    models.Index(fields=["conversion", "sequence_order"]),
                    models.Index(fields=["channel", "timestamp"]),
                    models.Index(fields=["platform", "timestamp"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="AnomalyAlert",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=64, db_index=True)),
                ("name", models.CharField(max_length=255)),
                ("metric", models.CharField(max_length=100, db_index=True)),
                ("platform", models.CharField(max_length=64, blank=True, db_index=True)),
                (
                    "method",
                    models.CharField(
                        max_length=32,
                        choices=ANOMALY_METHOD_CHOICES,
                        default="zscore",
                    ),
                ),
                (
                    "threshold",
                    models.DecimalField(
                        max_digits=10,
                        decimal_places=4,
                        default=3.0,
                        help_text="Sensitivity threshold (e.g. 3.0 for z-score, 1.5 for IQR)",
                    ),
                ),
                ("lookback_days", models.PositiveIntegerField(default=30)),
                (
                    "comparison_mode",
                    models.CharField(
                        max_length=32,
                        default="absolute",
                        help_text="Comparison: absolute, period_over_period, year_over_year",
                    ),
                ),
                (
                    "channels",
                    models.JSONField(
                        default=list,
                        help_text="Notification channels: [{type, recipients, channel, url}]",
                    ),
                ),
                ("cooldown_minutes", models.PositiveIntegerField(default=60)),
                ("enabled", models.BooleanField(default=True)),
                ("last_triggered_at", models.DateTimeField(null=True, blank=True)),
                ("trigger_count", models.PositiveIntegerField(default=0)),
                ("created_by", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={
                "db_table": "analytics_anomaly_alert",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "metric"]),
                    models.Index(fields=["tenant_id", "enabled"]),
                    models.Index(fields=["tenant_id", "method"]),
                    models.Index(fields=["tenant_id", "-last_triggered_at"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="AnomalyEvent",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                (
                    "alert",
                    models.ForeignKey(
                        AnomalyAlert,
                        on_delete=models.SET_NULL,
                        null=True,
                        blank=True,
                        related_name="events",
                    ),
                ),
                ("tenant_id", models.CharField(max_length=64, db_index=True)),
                ("metric", models.CharField(max_length=100, db_index=True)),
                (
                    "anomaly_type",
                    models.CharField(
                        max_length=32,
                        choices=ANOMALY_TYPE_CHOICES,
                        blank=True,
                    ),
                ),
                (
                    "severity",
                    models.CharField(
                        max_length=16,
                        choices=SEVERITY_CHOICES,
                        default="warning",
                    ),
                ),
                (
                    "expected_value",
                    models.DecimalField(
                        max_digits=15,
                        decimal_places=4,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "actual_value",
                    models.DecimalField(
                        max_digits=15,
                        decimal_places=4,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "deviation",
                    models.DecimalField(
                        max_digits=15,
                        decimal_places=4,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "z_score",
                    models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True),
                ),
                ("method", models.CharField(max_length=32, blank=True)),
                ("context", models.JSONField(default=dict, blank=True)),
                ("detected_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("acknowledged_at", models.DateTimeField(null=True, blank=True)),
                ("acknowledged_by", models.CharField(max_length=128, blank=True)),
                ("resolved_at", models.DateTimeField(null=True, blank=True)),
            ],
            options={
                "db_table": "analytics_anomaly_event",
                "ordering": ["-detected_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "metric", "-detected_at"]),
                    models.Index(fields=["tenant_id", "severity", "-detected_at"]),
                    models.Index(fields=["tenant_id", "anomaly_type"]),
                    models.Index(fields=["alert", "-detected_at"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="ExportJob",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=64, db_index=True)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                (
                    "query",
                    models.JSONField(
                        default=dict,
                        help_text="Query config: source, filters, date_range, aggregations",
                    ),
                ),
                (
                    "format",
                    models.CharField(
                        max_length=16,
                        choices=EXPORT_FORMAT_CHOICES,
                        default="csv",
                    ),
                ),
                (
                    "columns",
                    models.JSONField(
                        default=list,
                        help_text="Column names to include in the export",
                    ),
                ),
                ("file_path", models.CharField(max_length=512, blank=True)),
                ("download_url", models.URLField(blank=True)),
                ("download_expires_at", models.DateTimeField(null=True, blank=True)),
                (
                    "status",
                    models.CharField(
                        max_length=16,
                        choices=EXPORT_STATUS_CHOICES,
                        default="queued",
                    ),
                ),
                ("progress_percent", models.PositiveSmallIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(null=True, blank=True)),
                ("completed_at", models.DateTimeField(null=True, blank=True)),
                ("created_by", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={
                "db_table": "analytics_export_job",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "status", "-created_at"]),
                    models.Index(fields=["tenant_id", "-created_at"]),
                    models.Index(fields=["status", "-created_at"]),
                ],
            },
        ),
    ]
