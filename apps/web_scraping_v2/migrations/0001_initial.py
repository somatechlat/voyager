# Generated initial migration for web_scraping_v2

import uuid

from django.db import migrations, models


class Status(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ScrapeJob",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=128, db_index=True)),
                ("url", models.URLField(max_length=2048)),
                ("selector", models.CharField(max_length=512, blank=True, default="")),
                ("proxy_used", models.CharField(max_length=512, blank=True, default="")),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.PENDING,
                        db_index=True,
                    ),
                ),
                ("content_text", models.TextField(blank=True, default="")),
                ("content_html", models.TextField(blank=True, default="")),
                ("metadata", models.JSONField(default=dict, blank=True)),
                ("error_message", models.TextField(blank=True, default="")),
                ("started_at", models.DateTimeField(null=True, blank=True)),
                ("completed_at", models.DateTimeField(null=True, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "ws_scrape_jobs",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "status"]),
                    models.Index(fields=["tenant_id", "created_at"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="CompetitorMonitor",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=128, db_index=True)),
                ("name", models.CharField(max_length=255)),
                ("url", models.URLField(max_length=2048)),
                ("check_interval_minutes", models.PositiveIntegerField(default=60)),
                ("is_active", models.BooleanField(default=True, db_index=True)),
                ("last_checked_at", models.DateTimeField(null=True, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "ws_competitor_monitors",
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["tenant_id", "is_active"])],
            },
        ),
        migrations.CreateModel(
            name="CompetitorSnapshot",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                (
                    "competitor",
                    models.ForeignKey(
                        CompetitorMonitor,
                        on_delete=models.CASCADE,
                        related_name="snapshots",
                    ),
                ),
                ("url", models.URLField(max_length=2048)),
                ("content_hash", models.CharField(max_length=64, db_index=True)),
                ("content_text", models.TextField(blank=True, default="")),
                ("dom_structure", models.JSONField(default=dict, blank=True)),
                ("screenshot_path", models.CharField(max_length=1024, blank=True, default="")),
                ("prices", models.JSONField(default=list, blank=True)),
                ("products", models.JSONField(default=list, blank=True)),
                ("scraped_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "db_table": "ws_competitor_snapshots",
                "ordering": ["-scraped_at"],
                "indexes": [models.Index(fields=["competitor", "scraped_at"])],
            },
        ),
    ]
