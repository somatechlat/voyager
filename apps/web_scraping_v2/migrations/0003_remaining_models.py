# Generated initial migration for web_scraping_v2

import uuid

from django.db import migrations, models


class CompetitionLevel(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"


class Device(models.TextChoices):
    DESKTOP = "desktop", "Desktop"
    MOBILE = "mobile", "Mobile"
    TABLET = "tablet", "Tablet"


class FileType(models.TextChoices):
    IMAGE = "image", "Image"
    PDF = "pdf", "PDF"


class ModelType(models.TextChoices):
    BERT = "bert", "BERT"
    GPT = "gpt", "GPT"
    AUTO = "auto", "Auto"


class Sentiment(models.TextChoices):
    POSITIVE = "positive", "Positive"
    NEGATIVE = "negative", "Negative"
    NEUTRAL = "neutral", "Neutral"
    MIXED = "mixed", "Mixed"


class SentimentLabel(models.TextChoices):
    POSITIVE = "positive", "Positive"
    NEGATIVE = "negative", "Negative"
    NEUTRAL = "neutral", "Neutral"
    MIXED = "mixed", "Mixed"


class Status(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class Migration(migrations.Migration):

    initial = True

    dependencies = [("web_scraping_v2", "0002_additional_models")]

    operations = [
        migrations.CreateModel(
            name="SocialMention",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=128, db_index=True)),
                ("brand", models.CharField(max_length=255, db_index=True)),
                ("platform", models.CharField(max_length=50, db_index=True)),
                ("author", models.CharField(max_length=255, blank=True, default="")),
                ("text", models.TextField()),
                ("url", models.URLField(max_length=2048, blank=True, default="")),
                ("fingerprint", models.CharField(max_length=64, db_index=True)),
                (
                    "sentiment",
                    models.CharField(
                        max_length=20,
                        choices=SentimentLabel.choices,
                        blank=True,
                        default="",
                        db_index=True,
                    ),
                ),
                (
                    "sentiment_score",
                    models.DecimalField(
                        max_digits=4,
                        decimal_places=3,
                        null=True,
                        blank=True,
                    ),
                ),
                ("engagement", models.JSONField(default=dict, blank=True)),
                ("cross_platforms", models.JSONField(default=list, blank=True)),
                ("published_at", models.DateTimeField(null=True, blank=True, db_index=True)),
                ("collected_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "db_table": "ws_social_mentions",
                "ordering": ["-collected_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "collected_at"]),
                    models.Index(fields=["brand", "collected_at"]),
                    models.Index(fields=["sentiment"]),
                    models.Index(fields=["fingerprint"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="SentimentScore",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=128, db_index=True)),
                ("text", models.TextField()),
                ("text_hash", models.CharField(max_length=64, db_index=True)),
                ("source_type", models.CharField(max_length=50, blank=True, default="")),
                ("source_id", models.CharField(max_length=64, blank=True, default="")),
                (
                    "model",
                    models.CharField(
                        max_length=10,
                        choices=ModelType.choices,
                        default=ModelType.AUTO,
                    ),
                ),
                ("overall_sentiment", models.CharField(max_length=20, choices=Sentiment.choices)),
                ("overall_score", models.DecimalField(max_digits=4, decimal_places=3)),
                ("confidence", models.DecimalField(max_digits=4, decimal_places=3)),
                ("aspects", models.JSONField(default=list, blank=True)),
                ("emotions", models.JSONField(default=dict, blank=True)),
                ("language", models.CharField(max_length=10, default="en")),
                ("analyzed_at", models.DateTimeField(auto_now_add=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "ws_sentiment_scores",
                "ordering": ["-analyzed_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "analyzed_at"]),
                    models.Index(fields=["text_hash"]),
                    models.Index(fields=["overall_sentiment"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="SERPTracking",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=128, db_index=True)),
                ("keyword", models.CharField(max_length=500, db_index=True)),
                ("location_country", models.CharField(max_length=5, blank=True, default="")),
                ("location_region", models.CharField(max_length=100, blank=True, default="")),
                ("language", models.CharField(max_length=5, default="en")),
                (
                    "device",
                    models.CharField(
                        max_length=10,
                        choices=Device.choices,
                        default=Device.DESKTOP,
                    ),
                ),
                ("position", models.PositiveIntegerField(null=True, blank=True)),
                ("url", models.URLField(max_length=2048, blank=True, default="")),
                ("title", models.TextField(blank=True, default="")),
                ("description", models.TextField(blank=True, default="")),
                ("serp_features", models.JSONField(default=list, blank=True)),
                ("position_change", models.IntegerField(default=0)),
                ("search_volume", models.PositiveIntegerField(null=True, blank=True)),
                ("cpc", models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)),
                (
                    "competition",
                    models.CharField(
                        max_length=10,
                        choices=CompetitionLevel.choices,
                        blank=True,
                        default="",
                    ),
                ),
                ("tracked_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "ws_serp_trackings",
                "ordering": ["-tracked_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "keyword", "tracked_at"]),
                    models.Index(fields=["tenant_id", "device", "tracked_at"]),
                    models.Index(fields=["position"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="OCRJob",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=128, db_index=True)),
                ("file_url", models.CharField(max_length=2048)),
                (
                    "file_type",
                    models.CharField(
                        max_length=10,
                        choices=FileType.choices,
                        default=FileType.IMAGE,
                    ),
                ),
                ("languages", models.CharField(max_length=100, default="eng")),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.PENDING,
                        db_index=True,
                    ),
                ),
                ("extracted_text", models.TextField(blank=True, default="")),
                (
                    "avg_confidence",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                ("word_count", models.PositiveIntegerField(default=0)),
                ("words", models.JSONField(default=list, blank=True)),
                ("lines", models.JSONField(default=list, blank=True)),
                ("blocks", models.JSONField(default=list, blank=True)),
                ("tables", models.JSONField(default=list, blank=True)),
                ("preprocessing_applied", models.JSONField(default=list, blank=True)),
                ("error_message", models.TextField(blank=True, default="")),
                ("processing_time_ms", models.PositiveIntegerField(null=True, blank=True)),
                ("started_at", models.DateTimeField(null=True, blank=True)),
                ("completed_at", models.DateTimeField(null=True, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "ws_ocr_jobs",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "status"]),
                    models.Index(fields=["tenant_id", "created_at"]),
                ],
            },
        ),
    ]
