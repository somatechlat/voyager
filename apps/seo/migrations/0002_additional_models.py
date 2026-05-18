# Generated initial migration for seo

import uuid

from django.db import migrations, models


class Action(models.TextChoices):
    NONE = "none", "No Action"
    REVIEW = "review", "Review"
    DISAVOW = "disavow", "Disavow"


class LinkType(models.TextChoices):
    DOFOLLOW = "dofollow", "Dofollow"
    NOFOLLOW = "nofollow", "Nofollow"
    UGC = "ugc", "UGC"
    SPONSORED = "sponsored", "Sponsored"


class Priority(models.TextChoices):
    HIGH = "high", "High"
    MEDIUM = "medium", "Medium"
    LOW = "low", "Low"


class Severity(models.TextChoices):
    CRITICAL = "critical", "Critical"
    HIGH = "high", "High"
    MEDIUM = "medium", "Medium"
    LOW = "low", "Low"
    INFO = "info", "Info"


class Status(models.TextChoices):
    ACTIVE = "active", "Active"
    LOST = "lost", "Lost"
    NEW = "new", "New"
    DISAVOWED = "disavowed", "Disavowed"


class Migration(migrations.Migration):

    initial = True

    dependencies = [("seo", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Backlink",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=128, db_index=True)),
                (
                    "source_url",
                    models.URLField(max_length=2048, help_text="URL of the linking page"),
                ),
                (
                    "target_url",
                    models.URLField(max_length=2048, help_text="URL of the linked page"),
                ),
                ("anchor_text", models.TextField(blank=True, help_text="Link anchor text")),
                (
                    "referring_domain",
                    models.CharField(
                        max_length=255,
                        db_index=True,
                        blank=True,
                        help_text="Domain of the linking page",
                    ),
                ),
                (
                    "domain_authority",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "page_authority",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "spam_score",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                        help_text="Spam score 0-100",
                    ),
                ),
                ("is_toxic", models.BooleanField(default=False, db_index=True)),
                (
                    "toxicity_score",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        default=0.0,
                        help_text="Toxicity score 0-100",
                    ),
                ),
                (
                    "toxicity_reasons_json",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Reasons for toxicity flag",
                    ),
                ),
                (
                    "recommended_action",
                    models.CharField(
                        max_length=16,
                        choices=Action.choices,
                        default=Action.NONE,
                    ),
                ),
                (
                    "link_type",
                    models.CharField(
                        max_length=16,
                        choices=LinkType.choices,
                        default=LinkType.DOFOLLOW,
                    ),
                ),
                (
                    "is_sitewide",
                    models.BooleanField(
                        default=False,
                        help_text="Whether this is a site-wide link",
                    ),
                ),
                (
                    "source_outbound_links",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Total outbound links from source page",
                    ),
                ),
                ("source_language", models.CharField(max_length=10, blank=True)),
                (
                    "status",
                    models.CharField(
                        max_length=16,
                        choices=Status.choices,
                        default=Status.ACTIVE,
                        db_index=True,
                    ),
                ),
                ("first_seen", models.DateTimeField(null=True, blank=True)),
                ("last_seen", models.DateTimeField(null=True, blank=True)),
                ("last_checked_at", models.DateTimeField(null=True, blank=True)),
                ("metadata_json", models.JSONField(default=dict, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "voyager_backlink",
                "verbose_name": "Backlink",
                "verbose_name_plural": "Backlinks",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "referring_domain"]),
                    models.Index(fields=["tenant_id", "is_toxic"]),
                    models.Index(fields=["tenant_id", "status"]),
                    models.Index(fields=["tenant_id", "link_type"]),
                    models.Index(fields=["target_url", "-created_at"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="TechnicalCrawl",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=128, db_index=True)),
                (
                    "crawl_job_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        blank=True,
                        help_text="Parent crawl job identifier",
                    ),
                ),
                ("url", models.URLField(max_length=2048, db_index=True, help_text="Crawled URL")),
                (
                    "status_code",
                    models.PositiveIntegerField(
                        null=True,
                        blank=True,
                        help_text="HTTP response status",
                    ),
                ),
                (
                    "is_indexable",
                    models.BooleanField(
                        default=True,
                        help_text="Whether page can be indexed",
                    ),
                ),
                ("word_count", models.PositiveIntegerField(default=0)),
                ("title", models.TextField(blank=True)),
                ("meta_description", models.TextField(blank=True)),
                ("h1", models.TextField(blank=True)),
                ("h1_count", models.PositiveIntegerField(default=0)),
                ("canonical", models.URLField(max_length=2048, blank=True)),
                ("robots_meta", models.CharField(max_length=255, blank=True)),
                (
                    "hreflangs_json",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Hreflang tag declarations",
                    ),
                ),
                (
                    "lcp_ms",
                    models.PositiveIntegerField(
                        null=True,
                        blank=True,
                        help_text="Largest Contentful Paint in ms",
                    ),
                ),
                (
                    "fid_ms",
                    models.PositiveIntegerField(
                        null=True,
                        blank=True,
                        help_text="First Input Delay in ms",
                    ),
                ),
                (
                    "cls_score",
                    models.DecimalField(
                        max_digits=6,
                        decimal_places=4,
                        null=True,
                        blank=True,
                        help_text="Cumulative Layout Shift",
                    ),
                ),
                (
                    "ttfb_ms",
                    models.PositiveIntegerField(
                        null=True,
                        blank=True,
                        help_text="Time to First Byte in ms",
                    ),
                ),
                (
                    "page_size_kb",
                    models.PositiveIntegerField(
                        null=True,
                        blank=True,
                        help_text="Page size in kilobytes",
                    ),
                ),
                (
                    "load_time_ms",
                    models.PositiveIntegerField(
                        null=True,
                        blank=True,
                        help_text="Total page load time in ms",
                    ),
                ),
                (
                    "structured_data_json",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="JSON-LD structured data",
                    ),
                ),
                (
                    "schema_errors_json",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Schema validation errors",
                    ),
                ),
                (
                    "issues_json",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Technical issues detected",
                    ),
                ),
                (
                    "seo_score",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                        help_text="Page SEO score 0-100",
                    ),
                ),
                ("is_mobile_friendly", models.BooleanField(null=True, blank=True)),
                ("internal_links_json", models.JSONField(default=list, blank=True)),
                ("external_links_json", models.JSONField(default=list, blank=True)),
                ("broken_links_json", models.JSONField(default=list, blank=True)),
                ("metadata_json", models.JSONField(default=dict, blank=True)),
                ("crawled_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "voyager_technical_crawl",
                "verbose_name": "Technical Crawl",
                "verbose_name_plural": "Technical Crawls",
                "ordering": ["-crawled_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "url"]),
                    models.Index(fields=["tenant_id", "crawl_job_id"]),
                    models.Index(fields=["tenant_id", "-seo_score"]),
                    models.Index(fields=["tenant_id", "status_code"]),
                    models.Index(fields=["tenant_id", "is_indexable"]),
                    models.Index(fields=["tenant_id", "-crawled_at"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="ContentOptimization",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=128, db_index=True)),
                (
                    "url",
                    models.URLField(
                        max_length=2048,
                        blank=True,
                        help_text="URL of analyzed content",
                    ),
                ),
                (
                    "content_hash",
                    models.CharField(
                        max_length=64,
                        blank=True,
                        db_index=True,
                        help_text="SHA-256 hash of content",
                    ),
                ),
                ("target_keywords_json", models.JSONField(default=list, blank=True)),
                ("competitor_urls_json", models.JSONField(default=list, blank=True)),
                ("word_count", models.PositiveIntegerField(default=0)),
                ("sentence_count", models.PositiveIntegerField(default=0)),
                ("paragraph_count", models.PositiveIntegerField(default=0)),
                (
                    "flesch_reading_ease",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "flesch_kincaid_grade",
                    models.DecimalField(
                        max_digits=4,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "smog_index",
                    models.DecimalField(
                        max_digits=4,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "keyword_density_json",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Keyword density percentages per target",
                    ),
                ),
                (
                    "lsi_keywords_json",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Latent Semantic Indexing keywords found",
                    ),
                ),
                (
                    "keyword_placement_json",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Keyword positions in content",
                    ),
                ),
                (
                    "entities_json",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Named entities extracted",
                    ),
                ),
                (
                    "topics_covered_json",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Topics detected in content",
                    ),
                ),
                (
                    "missing_topics_json",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Topics competitors cover but this content doesn't",
                    ),
                ),
                ("competitor_avg_word_count", models.PositiveIntegerField(null=True, blank=True)),
                (
                    "competitor_avg_readability",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                ("competitor_common_topics_json", models.JSONField(default=list, blank=True)),
                (
                    "heading_structure_json",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="H1-H6 structure",
                    ),
                ),
                (
                    "content_score",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                        help_text="Overall score 0-100",
                    ),
                ),
                (
                    "readability_score",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "seo_score",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "uniqueness_score",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "recommendations_json",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Optimization recommendations with priority",
                    ),
                ),
                ("suggested_title", models.TextField(blank=True)),
                ("suggested_meta_description", models.TextField(blank=True)),
                ("metadata_json", models.JSONField(default=dict, blank=True)),
                ("analyzed_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "voyager_content_optimization",
                "verbose_name": "Content Optimization",
                "verbose_name_plural": "Content Optimizations",
                "ordering": ["-analyzed_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "url"]),
                    models.Index(fields=["tenant_id", "content_hash"]),
                    models.Index(fields=["tenant_id", "-content_score"]),
                    models.Index(fields=["tenant_id", "-analyzed_at"]),
                ],
            },
        ),
    ]
