# Generated initial migration for analytics_v2

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Dashboard",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=64, db_index=True)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("layout", models.JSONField(default=dict, help_text="Grid layout configuration")),
                (
                    "filters",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Default dashboard filters",
                    ),
                ),
                ("is_default", models.BooleanField(default=False)),
                ("is_shared", models.BooleanField(default=False)),
                (
                    "shared_with",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="User IDs with access",
                    ),
                ),
                ("created_by", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={
                "db_table": "analytics_dashboard",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "-created_at"]),
                    models.Index(fields=["tenant_id", "is_default"]),
                    models.Index(fields=["tenant_id", "created_by"]),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["tenant_id", "name"], name="%(app_label)s_dash_tenant_name_uniq"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="Widget",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                (
                    "dashboard",
                    models.ForeignKey(
                        Dashboard,
                        on_delete=models.CASCADE,
                        related_name="widgets",
                    ),
                ),
                ("widget_type", models.CharField(max_length=32, choices=WIDGET_TYPE_CHOICES)),
                ("title", models.CharField(max_length=255)),
                ("subtitle", models.CharField(max_length=255, blank=True)),
                (
                    "position",
                    models.JSONField(default=dict, help_text="Grid position: {x, y, w, h}"),
                ),
                (
                    "config",
                    models.JSONField(
                        default=dict,
                        help_text="Widget configuration: metrics, dimensions, filters, comparison",
                    ),
                ),
                (
                    "refresh_interval",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Auto-refresh interval in seconds; 0 = manual refresh",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "analytics_widget",
                "ordering": ["dashboard", "-updated_at"],
                "indexes": [models.Index(fields=["dashboard", "widget_type"])],
            },
        ),
        migrations.CreateModel(
            name="SavedQuery",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=64, db_index=True)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("sql", models.TextField(blank=True, help_text="Raw SQL or Trino federated query")),
                (
                    "query_builder",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Structured query builder config (alternative to SQL)",
                    ),
                ),
                (
                    "data_source",
                    models.CharField(
                        max_length=64,
                        default="clickhouse",
                        help_text="Primary data source: clickhouse, postgres, trino",
                    ),
                ),
                ("is_public", models.BooleanField(default=False)),
                ("last_run_at", models.DateTimeField(null=True, blank=True)),
                ("last_run_rows", models.PositiveIntegerField(default=0)),
                ("last_run_duration_ms", models.PositiveIntegerField(default=0)),
                ("created_by", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={
                "db_table": "analytics_saved_query",
                "ordering": ["-updated_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "is_public"]),
                    models.Index(fields=["tenant_id", "-updated_at"]),
                    models.Index(fields=["tenant_id", "data_source"]),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["tenant_id", "name"], name="%(app_label)s_sq_tenant_name_uniq"
                    )
                ],
            },
        ),
    ]
