"""Initial migration for the Web Scraping v2 module.

Creates all tables: scrape jobs, competitor monitoring, price tracking,
trend detection, social mentions, sentiment scores, SERP tracking, OCR jobs.
"""

from __future__ import annotations

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    """Initial migration creating all web scraping models."""

    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        # ScrapeJob
        migrations.CreateModel(
            name="ScrapeJob",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                ("url", models.URLField(max_length=2048)),
                (
                    "selector",
                    models.CharField(blank=True, default="", max_length=512),
                ),
                (
                    "proxy_used",
                    models.CharField(blank=True, default="", max_length=512),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "content_text",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "content_html",
                    models.TextField(blank=True, default=""),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "error_message",
                    models.TextField(blank=True, default=""),
                ),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "ws_scrape_jobs",
                "ordering": ["-created_at"],
            },
        ),
        # CompetitorMonitor
        migrations.CreateModel(
            name="CompetitorMonitor",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                ("name", models.CharField(max_length=255)),
                ("url", models.URLField(max_length=2048)),
                (
                    "check_interval_minutes",
                    models.PositiveIntegerField(default=60),
                ),
                (
                    "is_active",
                    models.BooleanField(db_index=True, default=True),
                ),
                (
                    "last_checked_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "ws_competitor_monitors",
                "ordering": ["-created_at"],
            },
        ),
        # CompetitorSnapshot
        migrations.CreateModel(
            name="CompetitorSnapshot",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("url", models.URLField(max_length=2048)),
                (
                    "content_hash",
                    models.CharField(db_index=True, max_length=64),
                ),
                (
                    "content_text",
                    models.TextField(blank=True, default=""),
                ),
                ("dom_structure", models.JSONField(blank=True, default=dict)),
                (
                    "screenshot_path",
                    models.CharField(blank=True, default="", max_length=1024),
                ),
                ("prices", models.JSONField(blank=True, default=list)),
                ("products", models.JSONField(blank=True, default=list)),
                (
                    "scraped_at",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
                (
                    "competitor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="snapshots",
                        to="web_scraping_v2.CompetitorMonitor",
                    ),
                ),
            ],
            options={
                "db_table": "ws_competitor_snapshots",
                "ordering": ["-scraped_at"],
            },
        ),
        # CompetitorChange
        migrations.CreateModel(
            name="CompetitorChange",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("url", models.URLField(max_length=2048)),
                (
                    "change_type",
                    models.CharField(
                        choices=[
                            ("new_content", "New Content"),
                            ("removed_content", "Removed Content"),
                            ("modified_content", "Modified Content"),
                            ("layout_change", "Layout Change"),
                            ("price_change", "Price Change"),
                            ("new_product", "New Product"),
                        ],
                        db_index=True,
                        max_length=30,
                    ),
                ),
                (
                    "change_details",
                    models.JSONField(blank=True, default=dict),
                ),
                (
                    "detected_at",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
                (
                    "competitor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="changes",
                        to="web_scraping_v2.CompetitorMonitor",
                    ),
                ),
            ],
            options={
                "db_table": "ws_competitor_changes",
                "ordering": ["-detected_at"],
            },
        ),
        # PriceTrack
        migrations.CreateModel(
            name="PriceTrack",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                (
                    "competitor_name",
                    models.CharField(db_index=True, max_length=255),
                ),
                (
                    "product_name",
                    models.CharField(db_index=True, max_length=500),
                ),
                (
                    "product_url",
                    models.URLField(blank=True, default="", max_length=2048),
                ),
                (
                    "price",
                    models.DecimalField(decimal_places=2, max_digits=12),
                ),
                ("currency", models.CharField(default="USD", max_length=3)),
                (
                    "original_price",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=12, null=True
                    ),
                ),
                (
                    "discount_pct",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=5, null=True
                    ),
                ),
                (
                    "normalized_price",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=12, null=True
                    ),
                ),
                (
                    "normalized_currency",
                    models.CharField(default="USD", max_length=3),
                ),
                (
                    "exchange_rate",
                    models.DecimalField(
                        blank=True, decimal_places=8, max_digits=15, null=True
                    ),
                ),
                (
                    "extraction_source",
                    models.CharField(
                        choices=[
                            ("css", "CSS Selector"),
                            ("json-ld", "JSON-LD Structured Data"),
                            ("regex", "Regex Fallback"),
                            ("api", "API Endpoint"),
                            ("manual", "Manual Entry"),
                        ],
                        default="css",
                        max_length=20,
                    ),
                ),
                (
                    "tracked_at",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "ws_price_tracks",
                "ordering": ["-tracked_at"],
            },
        ),
        # TrendDetection
        migrations.CreateModel(
            name="TrendDetection",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                (
                    "topic",
                    models.CharField(db_index=True, max_length=500),
                ),
                (
                    "source",
                    models.CharField(db_index=True, max_length=50),
                ),
                ("mention_count", models.PositiveIntegerField(default=0)),
                (
                    "trend_score",
                    models.DecimalField(decimal_places=2, default=0, max_digits=5),
                ),
                (
                    "velocity",
                    models.DecimalField(
                        decimal_places=4, default=0, max_digits=12
                    ),
                ),
                (
                    "acceleration",
                    models.DecimalField(
                        decimal_places=4, default=0, max_digits=12
                    ),
                ),
                (
                    "stage",
                    models.CharField(
                        choices=[
                            ("emerging", "Emerging"),
                            ("peaking", "Peaking"),
                            ("declining", "Declining"),
                            ("recovering", "Recovering"),
                        ],
                        db_index=True,
                        default="emerging",
                        max_length=20,
                    ),
                ),
                ("peak_date", models.DateTimeField(blank=True, null=True)),
                (
                    "estimated_lifespan_days",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                (
                    "industry_baseline",
                    models.PositiveIntegerField(default=0),
                ),
                ("data_points", models.JSONField(blank=True, default=list)),
                (
                    "tracked_at",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "ws_trend_detections",
                "ordering": ["-tracked_at"],
            },
        ),
        # SocialMention
        migrations.CreateModel(
            name="SocialMention",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                ("brand", models.CharField(db_index=True, max_length=255)),
                (
                    "platform",
                    models.CharField(db_index=True, max_length=50),
                ),
                (
                    "author",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                ("text", models.TextField()),
                (
                    "url",
                    models.URLField(blank=True, default="", max_length=2048),
                ),
                (
                    "fingerprint",
                    models.CharField(db_index=True, max_length=64),
                ),
                (
                    "sentiment",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("positive", "Positive"),
                            ("negative", "Negative"),
                            ("neutral", "Neutral"),
                            ("mixed", "Mixed"),
                        ],
                        db_index=True,
                        default="",
                        max_length=20,
                    ),
                ),
                (
                    "sentiment_score",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=4, null=True
                    ),
                ),
                ("engagement", models.JSONField(blank=True, default=dict)),
                (
                    "cross_platforms",
                    models.JSONField(blank=True, default=list),
                ),
                (
                    "published_at",
                    models.DateTimeField(blank=True, db_index=True, null=True),
                ),
                (
                    "collected_at",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
            ],
            options={
                "db_table": "ws_social_mentions",
                "ordering": ["-collected_at"],
            },
        ),
        # SentimentScore
        migrations.CreateModel(
            name="SentimentScore",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                ("text", models.TextField()),
                (
                    "text_hash",
                    models.CharField(db_index=True, max_length=64),
                ),
                (
                    "source_type",
                    models.CharField(blank=True, default="", max_length=50),
                ),
                (
                    "source_id",
                    models.CharField(blank=True, default="", max_length=64),
                ),
                (
                    "model",
                    models.CharField(
                        choices=[
                            ("bert", "BERT"),
                            ("gpt", "GPT"),
                            ("auto", "Auto"),
                        ],
                        default="auto",
                        max_length=10,
                    ),
                ),
                (
                    "overall_sentiment",
                    models.CharField(
                        choices=[
                            ("positive", "Positive"),
                            ("negative", "Negative"),
                            ("neutral", "Neutral"),
                            ("mixed", "Mixed"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "overall_score",
                    models.DecimalField(decimal_places=3, max_digits=4),
                ),
                (
                    "confidence",
                    models.DecimalField(decimal_places=3, max_digits=4),
                ),
                ("aspects", models.JSONField(blank=True, default=list)),
                ("emotions", models.JSONField(blank=True, default=dict)),
                ("language", models.CharField(default="en", max_length=10)),
                ("analyzed_at", models.DateTimeField(auto_now_add=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "ws_sentiment_scores",
                "ordering": ["-analyzed_at"],
            },
        ),
        # SERPTracking
        migrations.CreateModel(
            name="SERPTracking",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                (
                    "keyword",
                    models.CharField(db_index=True, max_length=500),
                ),
                (
                    "location_country",
                    models.CharField(blank=True, default="", max_length=5),
                ),
                (
                    "location_region",
                    models.CharField(blank=True, default="", max_length=100),
                ),
                ("language", models.CharField(default="en", max_length=5)),
                (
                    "device",
                    models.CharField(
                        choices=[
                            ("desktop", "Desktop"),
                            ("mobile", "Mobile"),
                            ("tablet", "Tablet"),
                        ],
                        default="desktop",
                        max_length=10,
                    ),
                ),
                (
                    "position",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                (
                    "url",
                    models.URLField(blank=True, default="", max_length=2048),
                ),
                (
                    "title",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "description",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "serp_features",
                    models.JSONField(blank=True, default=list),
                ),
                ("position_change", models.IntegerField(default=0)),
                (
                    "search_volume",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                (
                    "cpc",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=8, null=True
                    ),
                ),
                (
                    "competition",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("low", "Low"),
                            ("medium", "Medium"),
                            ("high", "High"),
                        ],
                        default="",
                        max_length=10,
                    ),
                ),
                (
                    "tracked_at",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "ws_serp_trackings",
                "ordering": ["-tracked_at"],
            },
        ),
        # OCRJob
        migrations.CreateModel(
            name="OCRJob",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                ("file_url", models.CharField(max_length=2048)),
                (
                    "file_type",
                    models.CharField(
                        choices=[("image", "Image"), ("pdf", "PDF")],
                        default="image",
                        max_length=10,
                    ),
                ),
                ("languages", models.CharField(default="eng", max_length=100)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "extracted_text",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "avg_confidence",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=5, null=True
                    ),
                ),
                ("word_count", models.PositiveIntegerField(default=0)),
                ("words", models.JSONField(blank=True, default=list)),
                ("lines", models.JSONField(blank=True, default=list)),
                ("blocks", models.JSONField(blank=True, default=list)),
                ("tables", models.JSONField(blank=True, default=list)),
                (
                    "preprocessing_applied",
                    models.JSONField(blank=True, default=list),
                ),
                (
                    "error_message",
                    models.TextField(blank=True, default=""),
                ),
                (
                    "processing_time_ms",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "ws_ocr_jobs",
                "ordering": ["-created_at"],
            },
        ),
        # Indexes
        migrations.AddIndex(
            model_name="scrapejob",
            index=models.Index(
                fields=["tenant_id", "status"], name="ws_scrape_tenant_status"
            ),
        ),
        migrations.AddIndex(
            model_name="scrapejob",
            index=models.Index(
                fields=["tenant_id", "created_at"], name="ws_scrape_tenant_created"
            ),
        ),
        migrations.AddIndex(
            model_name="competitormonitor",
            index=models.Index(
                fields=["tenant_id", "is_active"],
                name="ws_comp_monitor_tenant_active",
            ),
        ),
        migrations.AddIndex(
            model_name="competitorsnapshot",
            index=models.Index(
                fields=["competitor", "scraped_at"],
                name="ws_comp_snap_comp_scraped",
            ),
        ),
        migrations.AddIndex(
            model_name="competitorchange",
            index=models.Index(
                fields=["competitor", "detected_at"],
                name="ws_comp_chg_comp_detected",
            ),
        ),
        migrations.AddIndex(
            model_name="pricetrack",
            index=models.Index(
                fields=["tenant_id", "competitor_name", "product_name"],
                name="ws_price_tenant_comp_prod",
            ),
        ),
        migrations.AddIndex(
            model_name="pricetrack",
            index=models.Index(
                fields=["tenant_id", "tracked_at"],
                name="ws_price_tenant_tracked",
            ),
        ),
        migrations.AddIndex(
            model_name="trenddetection",
            index=models.Index(
                fields=["tenant_id", "topic", "tracked_at"],
                name="ws_trend_tenant_topic_tracked",
            ),
        ),
        migrations.AddIndex(
            model_name="trenddetection",
            index=models.Index(
                fields=["tenant_id", "stage"], name="ws_trend_tenant_stage"
            ),
        ),
        migrations.AddIndex(
            model_name="socialmention",
            index=models.Index(
                fields=["tenant_id", "collected_at"],
                name="ws_social_tenant_collected",
            ),
        ),
        migrations.AddIndex(
            model_name="socialmention",
            index=models.Index(
                fields=["brand", "collected_at"], name="ws_social_brand_collected"
            ),
        ),
        migrations.AddIndex(
            model_name="socialmention",
            index=models.Index(
                fields=["fingerprint"], name="ws_social_fingerprint"
            ),
        ),
        migrations.AddIndex(
            model_name="sentimentscore",
            index=models.Index(
                fields=["tenant_id", "analyzed_at"],
                name="ws_sent_tenant_analyzed",
            ),
        ),
        migrations.AddIndex(
            model_name="sentimentscore",
            index=models.Index(
                fields=["text_hash"], name="ws_sent_text_hash"
            ),
        ),
        migrations.AddIndex(
            model_name="serptracking",
            index=models.Index(
                fields=["tenant_id", "keyword", "tracked_at"],
                name="ws_serp_tenant_kw_tracked",
            ),
        ),
        migrations.AddIndex(
            model_name="serptracking",
            index=models.Index(
                fields=["tenant_id", "device", "tracked_at"],
                name="ws_serp_tenant_device_tracked",
            ),
        ),
        migrations.AddIndex(
            model_name="ocrjob",
            index=models.Index(
                fields=["tenant_id", "status"], name="ws_ocr_tenant_status"
            ),
        ),
        migrations.AddIndex(
            model_name="ocrjob",
            index=models.Index(
                fields=["tenant_id", "created_at"], name="ws_ocr_tenant_created"
            ),
        ),
    ]
