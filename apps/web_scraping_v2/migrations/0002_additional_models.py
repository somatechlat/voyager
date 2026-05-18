# Generated initial migration for web_scraping_v2

import uuid

from django.db import migrations, models


class ChangeType(models.TextChoices):
    NEW_CONTENT = "new_content", "New Content"
    REMOVED_CONTENT = "removed_content", "Removed Content"
    MODIFIED_CONTENT = "modified_content", "Modified Content"
    LAYOUT_CHANGE = "layout_change", "Layout Change"
    PRICE_CHANGE = "price_change", "Price Change"
    NEW_PRODUCT = "new_product", "New Product"


class ExtractionSource(models.TextChoices):
    CSS = "css", "CSS Selector"
    JSON_LD = "json-ld", "JSON-LD Structured Data"
    REGEX = "regex", "Regex Fallback"
    API = "api", "API Endpoint"
    MANUAL = "manual", "Manual Entry"


class Stage(models.TextChoices):
    EMERGING = "emerging", "Emerging"
    PEAKING = "peaking", "Peaking"
    DECLINING = "declining", "Declining"
    RECOVERING = "recovering", "Recovering"


class Migration(migrations.Migration):

    initial = True

    dependencies = [("web_scraping_v2", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="CompetitorChange",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                (
                    "competitor",
                    models.ForeignKey(
                        CompetitorMonitor,
                        on_delete=models.CASCADE,
                        related_name="changes",
                    ),
                ),
                ("url", models.URLField(max_length=2048)),
                (
                    "change_type",
                    models.CharField(
                        max_length=30,
                        choices=ChangeType.choices,
                        db_index=True,
                    ),
                ),
                ("change_details", models.JSONField(default=dict, blank=True)),
                ("detected_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "db_table": "ws_competitor_changes",
                "ordering": ["-detected_at"],
                "indexes": [models.Index(fields=["competitor", "detected_at"])],
            },
        ),
        migrations.CreateModel(
            name="PriceTrack",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=128, db_index=True)),
                ("competitor_name", models.CharField(max_length=255, db_index=True)),
                ("product_name", models.CharField(max_length=500, db_index=True)),
                ("product_url", models.URLField(max_length=2048, blank=True, default="")),
                ("price", models.DecimalField(max_digits=12, decimal_places=2)),
                ("currency", models.CharField(max_length=3, default="USD")),
                (
                    "original_price",
                    models.DecimalField(
                        max_digits=12,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "discount_pct",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "normalized_price",
                    models.DecimalField(
                        max_digits=12,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                ("normalized_currency", models.CharField(max_length=3, default="USD")),
                (
                    "exchange_rate",
                    models.DecimalField(
                        max_digits=15,
                        decimal_places=8,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "extraction_source",
                    models.CharField(
                        max_length=20,
                        choices=ExtractionSource.choices,
                        default=ExtractionSource.CSS,
                    ),
                ),
                ("tracked_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "ws_price_tracks",
                "ordering": ["-tracked_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "competitor_name", "product_name"]),
                    models.Index(fields=["tenant_id", "tracked_at"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="TrendDetection",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=128, db_index=True)),
                ("topic", models.CharField(max_length=500, db_index=True)),
                ("source", models.CharField(max_length=50, db_index=True)),
                ("mention_count", models.PositiveIntegerField(default=0)),
                ("trend_score", models.DecimalField(max_digits=5, decimal_places=2, default=0)),
                ("velocity", models.DecimalField(max_digits=12, decimal_places=4, default=0)),
                ("acceleration", models.DecimalField(max_digits=12, decimal_places=4, default=0)),
                (
                    "stage",
                    models.CharField(
                        max_length=20,
                        choices=Stage.choices,
                        default=Stage.EMERGING,
                        db_index=True,
                    ),
                ),
                ("peak_date", models.DateTimeField(null=True, blank=True)),
                ("estimated_lifespan_days", models.PositiveIntegerField(null=True, blank=True)),
                ("industry_baseline", models.PositiveIntegerField(default=0)),
                ("data_points", models.JSONField(default=list, blank=True)),
                ("tracked_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "ws_trend_detections",
                "ordering": ["-tracked_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "topic", "tracked_at"]),
                    models.Index(fields=["tenant_id", "stage"]),
                    models.Index(fields=["source", "tracked_at"]),
                ],
            },
        ),
    ]
