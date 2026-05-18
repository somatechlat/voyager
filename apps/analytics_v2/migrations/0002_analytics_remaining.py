"""Initial migration for analytics_v2 app (part 2).

Creates Touchpoint, AnomalyAlert, AnomalyEvent, ExportJob, and SavedQuery.
"""

from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Migration creating remaining analytics_v2 models."""

    dependencies = [("analytics_v2", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Touchpoint",
            fields=[
                ("id", models.UUIDField(default=models.UUIDField().default, editable=False, primary_key=True, serialize=False)),
                ("conversion", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="touchpoints", to="analytics_v2.conversionpath")),
                ("sequence_order", models.PositiveIntegerField(default=1)),
                ("touchpoint_type", models.CharField(choices=[("impression", "Impression"), ("click", "Click"), ("view", "View"), ("engagement", "Engagement"), ("visit", "Website Visit"), ("signup", "Sign Up"), ("download", "Download"), ("email_open", "Email Open"), ("email_click", "Email Click"), ("ad_click", "Ad Click"), ("organic_search", "Organic Search"), ("social_click", "Social Click"), ("referral", "Referral"), ("direct", "Direct"), ("conversion", "Conversion")], default="click", max_length=32)),
                ("channel", models.CharField(blank=True, db_index=True, max_length=64)),
                ("platform", models.CharField(blank=True, db_index=True, max_length=64)),
                ("campaign", models.CharField(blank=True, max_length=255)),
                ("ad_group", models.CharField(blank=True, max_length=255)),
                ("creative", models.CharField(blank=True, max_length=255)),
                ("landing_page", models.URLField(blank=True)),
                ("referrer", models.URLField(blank=True)),
                ("device_type", models.CharField(blank=True, max_length=32)),
                ("geographic", models.JSONField(blank=True, default=dict)),
                ("timestamp", models.DateTimeField(db_index=True)),
                ("credit", models.DecimalField(decimal_places=4, default=0, help_text="Attribution credit (0.0 - 1.0)", max_digits=5)),
                ("revenue_attributed", models.DecimalField(decimal_places=4, default=0, max_digits=15)),
                ("time_since_previous_hours", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
            ],
            options={"db_table": "analytics_touchpoint", "ordering": ["conversion", "sequence_order"]},
        ),
        migrations.AddIndex(
            model_name="touchpoint",
            index=models.Index(fields=["conversion", "sequence_order"], name="an_tp_conv_seq"),
        ),
        migrations.CreateModel(
            name="AnomalyAlert",
            fields=[
                ("id", models.UUIDField(default=models.UUIDField().default, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.CharField(db_index=True, max_length=64)),
                ("name", models.CharField(max_length=255)),
                ("metric", models.CharField(db_index=True, max_length=100)),
                ("platform", models.CharField(blank=True, db_index=True, max_length=64)),
                ("method", models.CharField(choices=[("zscore", "Z-Score"), ("iqr", "Interquartile Range (IQR)"), ("seasonal_decomposition", "Seasonal Decomposition (STL)"), ("mad", "Median Absolute Deviation"), ("ewma", "Exponentially Weighted Moving Average")], default="zscore", max_length=32)),
                ("threshold", models.DecimalField(decimal_places=4, default=3.0, help_text="Sensitivity threshold", max_digits=10)),
                ("lookback_days", models.PositiveIntegerField(default=30)),
                ("comparison_mode", models.CharField(default="absolute", help_text="Comparison mode", max_length=32)),
                ("channels", models.JSONField(default=list, help_text="Notification channels")),
                ("cooldown_minutes", models.PositiveIntegerField(default=60)),
                ("enabled", models.BooleanField(default=True)),
                ("last_triggered_at", models.DateTimeField(blank=True, null=True)),
                ("trigger_count", models.PositiveIntegerField(default=0)),
                ("created_by", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={"db_table": "analytics_anomaly_alert", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="anomalyalert",
            index=models.Index(fields=["tenant_id", "enabled"], name="an_alert_tenant_en"),
        ),
        migrations.CreateModel(
            name="AnomalyEvent",
            fields=[
                ("id", models.UUIDField(default=models.UUIDField().default, editable=False, primary_key=True, serialize=False)),
                ("alert", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="events", to="analytics_v2.anomalyalert")),
                ("tenant_id", models.CharField(db_index=True, max_length=64)),
                ("metric", models.CharField(db_index=True, max_length=100)),
                ("anomaly_type", models.CharField(blank=True, choices=[("spike", "Spike"), ("drop", "Drop"), ("trend_change", "Trend Change"), ("seasonal_shift", "Seasonal Shift"), ("level_shift", "Level Shift"), ("volatility_change", "Volatility Change")], max_length=32)),
                ("severity", models.CharField(choices=[("info", "Info"), ("warning", "Warning"), ("critical", "Critical")], default="warning", max_length=16)),
                ("expected_value", models.DecimalField(blank=True, decimal_places=4, max_digits=15, null=True)),
                ("actual_value", models.DecimalField(blank=True, decimal_places=4, max_digits=15, null=True)),
                ("deviation", models.DecimalField(blank=True, decimal_places=4, max_digits=15, null=True)),
                ("z_score", models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ("method", models.CharField(blank=True, max_length=32)),
                ("context", models.JSONField(blank=True, default=dict)),
                ("detected_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("acknowledged_at", models.DateTimeField(blank=True, null=True)),
                ("acknowledged_by", models.CharField(blank=True, max_length=128)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"db_table": "analytics_anomaly_event", "ordering": ["-detected_at"]},
        ),
        migrations.AddIndex(
            model_name="anomalyevent",
            index=models.Index(fields=["tenant_id", "metric", "-detected_at"], name="an_evt_tenant_metric_dt"),
        ),
        migrations.AddIndex(
            model_name="anomalyevent",
            index=models.Index(fields=["tenant_id", "severity", "-detected_at"], name="an_evt_tenant_sev_dt"),
        ),
        migrations.CreateModel(
            name="ExportJob",
            fields=[
                ("id", models.UUIDField(default=models.UUIDField().default, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.CharField(db_index=True, max_length=64)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("query", models.JSONField(default=dict, help_text="Query config")),
                ("format", models.CharField(choices=[("csv", "CSV"), ("json", "JSON"), ("excel", "Excel (.xlsx)"), ("ndjson", "Newline-Delimited JSON")], default="csv", max_length=16)),
                ("columns", models.JSONField(default=list, help_text="Column names")),
                ("row_count", models.PositiveBigIntegerField(default=0)),
                ("file_size_bytes", models.PositiveBigIntegerField(default=0)),
                ("file_path", models.CharField(blank=True, max_length=512)),
                ("download_url", models.URLField(blank=True)),
                ("download_expires_at", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed"), ("cancelled", "Cancelled"), ("expired", "Expired")], default="queued", max_length=16)),
                ("progress_percent", models.PositiveSmallIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={"db_table": "analytics_export_job", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="exportjob",
            index=models.Index(fields=["tenant_id", "status", "-created_at"], name="an_exp_tenant_status"),
        ),
        migrations.CreateModel(
            name="SavedQuery",
            fields=[
                ("id", models.UUIDField(default=models.UUIDField().default, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.CharField(db_index=True, max_length=64)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("sql", models.TextField(blank=True, help_text="Raw SQL or Trino federated query")),
                ("query_builder", models.JSONField(blank=True, default=dict, help_text="Structured query builder config")),
                ("data_source", models.CharField(default="clickhouse", help_text="Primary data source", max_length=64)),
                ("is_public", models.BooleanField(default=False)),
                ("last_run_at", models.DateTimeField(blank=True, null=True)),
                ("last_run_rows", models.PositiveIntegerField(default=0)),
                ("last_run_duration_ms", models.PositiveIntegerField(default=0)),
                ("created_by", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={"db_table": "analytics_saved_query", "ordering": ["-updated_at"]},
        ),
        migrations.AddIndex(
            model_name="savedquery",
            index=models.Index(fields=["tenant_id", "is_public"], name="an_sq_tenant_public"),
        ),
        migrations.AlterUniqueTogether(name="savedquery", unique_together={("tenant_id", "name")}),
    ]
