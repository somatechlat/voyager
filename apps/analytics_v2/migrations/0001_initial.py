"""Initial migration for analytics_v2 app (part 1).

Creates Dashboard, Widget, ReportTemplate, ReportSchedule, AttributionModel,
and ConversionPath.
"""

from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Initial migration for analytics_v2 models (part 1)."""

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Dashboard",
            fields=[
                ("id", models.UUIDField(default=models.UUIDField().default, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.CharField(db_index=True, max_length=64)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("layout", models.JSONField(default=dict, help_text="Grid layout configuration")),
                ("filters", models.JSONField(blank=True, default=dict, help_text="Default dashboard filters")),
                ("is_default", models.BooleanField(default=False)),
                ("is_shared", models.BooleanField(default=False)),
                ("shared_with", models.JSONField(blank=True, default=list, help_text="User IDs with access")),
                ("created_by", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={"db_table": "analytics_dashboard", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="dashboard",
            index=models.Index(fields=["tenant_id", "-created_at"], name="an_dash_tenant_created"),
        ),
        migrations.AddIndex(
            model_name="dashboard",
            index=models.Index(fields=["tenant_id", "is_default"], name="an_dash_tenant_default"),
        ),
        migrations.AlterUniqueTogether(name="dashboard", unique_together={("tenant_id", "name")}),
        migrations.CreateModel(
            name="Widget",
            fields=[
                ("id", models.UUIDField(default=models.UUIDField().default, editable=False, primary_key=True, serialize=False)),
                ("widget_type", models.CharField(choices=[
                    ("kpi_card", "KPI Card"), ("line_chart", "Line Chart"), ("bar_chart", "Bar Chart"),
                    ("pie_chart", "Pie Chart"), ("heatmap", "Heatmap"), ("funnel", "Funnel"),
                    ("table", "Table"), ("area_chart", "Area Chart"), ("scatter_plot", "Scatter Plot"),
                    ("gauge", "Gauge"), ("scorecard", "Scorecard"), ("treemap", "Treemap"),
                    ("cohort_table", "Cohort Table"), ("pivot_table", "Pivot Table"),
                    ("comparison_bar", "Comparison Bar"), ("sparkline", "Sparkline"),
                    ("top_list", "Top List"), ("metric_trend", "Metric Trend"),
                ], max_length=32)),
                ("title", models.CharField(max_length=255)),
                ("subtitle", models.CharField(blank=True, max_length=255)),
                ("position", models.JSONField(default=dict, help_text="Grid position: {x, y, w, h}")),
                ("config", models.JSONField(default=dict, help_text="Widget configuration: metrics, dimensions, filters")),
                ("refresh_interval", models.PositiveIntegerField(default=0, help_text="Auto-refresh interval in seconds")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("dashboard", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="widgets", to="analytics_v2.dashboard")),
            ],
            options={"db_table": "analytics_widget", "ordering": ["dashboard", "-updated_at"]},
        ),
        migrations.AddIndex(
            model_name="widget",
            index=models.Index(fields=["dashboard", "widget_type"], name="an_widget_dash_type"),
        ),
        migrations.CreateModel(
            name="ReportTemplate",
            fields=[
                ("id", models.UUIDField(default=models.UUIDField().default, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.CharField(db_index=True, max_length=64)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("category", models.CharField(db_index=True, default="general", help_text="Report category", max_length=64)),
                ("config", models.JSONField(default=dict, help_text="Metrics, dimensions, filters, visualizations")),
                ("format", models.CharField(choices=[("pdf", "PDF"), ("csv", "CSV"), ("excel", "Excel"), ("json", "JSON")], default="pdf", max_length=16)),
                ("is_favorite", models.BooleanField(default=False)),
                ("created_by", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={"db_table": "analytics_report_template", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="reporttemplate",
            index=models.Index(fields=["tenant_id", "category"], name="an_rpt_tenant_cat"),
        ),
        migrations.AlterUniqueTogether(name="reporttemplate", unique_together={("tenant_id", "name")}),
        migrations.CreateModel(
            name="ReportSchedule",
            fields=[
                ("id", models.UUIDField(default=models.UUIDField().default, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.CharField(db_index=True, max_length=64)),
                ("template", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="schedules", to="analytics_v2.reporttemplate")),
                ("name", models.CharField(max_length=255)),
                ("frequency", models.CharField(choices=[("once", "Once"), ("hourly", "Hourly"), ("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly")], default="weekly", max_length=16)),
                ("cron_expression", models.CharField(blank=True, help_text="Optional cron", max_length=128)),
                ("next_run_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("last_run_at", models.DateTimeField(blank=True, null=True)),
                ("last_run_status", models.CharField(choices=[("draft", "Draft"), ("ready", "Ready"), ("scheduled", "Scheduled"), ("generating", "Generating"), ("completed", "Completed"), ("failed", "Failed"), ("cancelled", "Cancelled")], default="draft", max_length=16)),
                ("last_run_result", models.JSONField(blank=True, default=dict)),
                ("delivery", models.JSONField(default=dict, help_text="Delivery channels")),
                ("timezone", models.CharField(default="UTC", max_length=64)),
                ("is_active", models.BooleanField(default=True)),
                ("created_by", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={"db_table": "analytics_report_schedule", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="reportschedule",
            index=models.Index(fields=["tenant_id", "is_active", "next_run_at"], name="an_rsch_tenant_active_next"),
        ),
        migrations.CreateModel(
            name="AttributionModel",
            fields=[
                ("id", models.UUIDField(default=models.UUIDField().default, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.CharField(db_index=True, max_length=64)),
                ("name", models.CharField(max_length=255)),
                ("model_type", models.CharField(choices=[("first_touch", "First Touch"), ("last_touch", "Last Touch"), ("linear", "Linear"), ("time_decay", "Time Decay"), ("position_based", "Position Based (U-Shaped)"), ("data_driven", "Data Driven (Markov Chain)")], default="last_touch", max_length=32)),
                ("config", models.JSONField(default=dict, help_text="Model-specific parameters")),
                ("lookback_window_days", models.PositiveIntegerField(default=30)),
                ("is_default", models.BooleanField(default=False)),
                ("created_by", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={"db_table": "analytics_attribution_model", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="attributionmodel",
            index=models.Index(fields=["tenant_id", "model_type"], name="an_attr_tenant_type"),
        ),
        migrations.AlterUniqueTogether(name="attributionmodel", unique_together={("tenant_id", "name")}),
        migrations.CreateModel(
            name="ConversionPath",
            fields=[
                ("id", models.UUIDField(default=models.UUIDField().default, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.CharField(db_index=True, max_length=64)),
                ("attribution_model", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="conversion_paths", to="analytics_v2.attributionmodel")),
                ("conversion_id", models.CharField(db_index=True, max_length=255)),
                ("user_id", models.CharField(blank=True, db_index=True, max_length=255)),
                ("conversion_value", models.DecimalField(decimal_places=4, default=0, max_digits=15)),
                ("conversion_date", models.DateTimeField(db_index=True)),
                ("currency", models.CharField(default="USD", max_length=3)),
                ("channel", models.CharField(blank=True, db_index=True, max_length=64)),
                ("campaign", models.CharField(blank=True, max_length=255)),
                ("total_touchpoints", models.PositiveIntegerField(default=0)),
                ("time_to_conversion_hours", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={"db_table": "analytics_conversion_path", "ordering": ["-conversion_date"]},
        ),
    ]
