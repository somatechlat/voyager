# Generated initial migration for seo

import uuid

from django.db import migrations, models


class CommercialIntent(models.TextChoices):
    INFORMATIONAL = "informational", "Informational"
    NAVIGATIONAL = "navigational", "Navigational"
    COMMERCIAL = "commercial", "Commercial"
    TRANSACTIONAL = "transactional", "Transactional"


class Grade(models.TextChoices):
    A = "A", "A (90-100)"
    B = "B", "B (75-89)"
    C = "C", "C (60-74)"
    D = "D", "D (45-59)"
    F = "F", "F (0-44)"


class TrendDirection(models.TextChoices):
    RISING = "rising", "Rising"
    FALLING = "falling", "Falling"
    STABLE = "stable", "Stable"


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="KeywordCluster",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=128, db_index=True)),
                (
                    "label",
                    models.CharField(max_length=255, help_text="Central theme of the cluster"),
                ),
                (
                    "total_volume",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Sum of monthly volumes",
                    ),
                ),
                (
                    "avg_difficulty",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        default=0.0,
                        help_text="Average keyword difficulty",
                    ),
                ),
                (
                    "priority_score",
                    models.DecimalField(
                        max_digits=10,
                        decimal_places=4,
                        default=0.0,
                        help_text="Cluster priority = total_volume * (1 - avg_difficulty/100)",
                    ),
                ),
                (
                    "embedding_vector",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Cluster centroid embedding",
                    ),
                ),
                ("metadata_json", models.JSONField(default=dict, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "voyager_keyword_cluster",
                "verbose_name": "Keyword Cluster",
                "verbose_name_plural": "Keyword Clusters",
                "ordering": ["-priority_score"],
                "indexes": [
                    models.Index(fields=["tenant_id", "-priority_score"]),
                    models.Index(fields=["tenant_id", "-created_at"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="Keyword",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=128, db_index=True)),
                (
                    "keyword",
                    models.CharField(
                        max_length=500,
                        db_index=True,
                        help_text="The keyword phrase",
                    ),
                ),
                (
                    "location",
                    models.CharField(
                        max_length=10,
                        default="US",
                        help_text="ISO 3166-1 country code",
                    ),
                ),
                (
                    "language",
                    models.CharField(
                        max_length=10,
                        default="en",
                        help_text="ISO 639-1 language code",
                    ),
                ),
                (
                    "monthly_volume",
                    models.PositiveIntegerField(
                        null=True,
                        blank=True,
                        help_text="Monthly search volume",
                    ),
                ),
                (
                    "difficulty",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                        help_text="Keyword difficulty 0-100",
                    ),
                ),
                (
                    "cpc",
                    models.DecimalField(
                        max_digits=8,
                        decimal_places=2,
                        null=True,
                        blank=True,
                        help_text="Cost per click in USD",
                    ),
                ),
                (
                    "trend_direction",
                    models.CharField(
                        max_length=20,
                        choices=TrendDirection.choices,
                        blank=True,
                        help_text="12-month trend direction",
                    ),
                ),
                (
                    "trend_growth",
                    models.DecimalField(
                        max_digits=6,
                        decimal_places=4,
                        default=0.0,
                        help_text="Trend growth rate (e.g. 0.15 = 15% growth)",
                    ),
                ),
                (
                    "current_position",
                    models.PositiveIntegerField(
                        null=True,
                        blank=True,
                        help_text="Current SERP position",
                    ),
                ),
                (
                    "previous_position",
                    models.PositiveIntegerField(
                        null=True,
                        blank=True,
                        help_text="Previous SERP position",
                    ),
                ),
                (
                    "position_change",
                    models.IntegerField(
                        default=0,
                        help_text="Positive = improved, negative = dropped",
                    ),
                ),
                (
                    "target_url",
                    models.URLField(
                        max_length=2048,
                        blank=True,
                        help_text="Target URL for this keyword",
                    ),
                ),
                (
                    "serp_features_json",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Detected SERP features",
                    ),
                ),
                (
                    "cluster",
                    models.ForeignKey(
                        KeywordCluster,
                        on_delete=models.SET_NULL,
                        null=True,
                        blank=True,
                        related_name="keywords",
                    ),
                ),
                (
                    "opportunity_score",
                    models.DecimalField(
                        max_digits=8,
                        decimal_places=4,
                        default=0.0,
                        help_text="Computed opportunity score",
                    ),
                ),
                (
                    "commercial_intent",
                    models.CharField(
                        max_length=20,
                        choices=CommercialIntent.choices,
                        blank=True,
                        help_text="Detected commercial intent",
                    ),
                ),
                (
                    "embedding_vector",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Keyword embedding vector",
                    ),
                ),
                (
                    "is_tracked",
                    models.BooleanField(
                        default=False,
                        db_index=True,
                        help_text="Whether rank tracking is enabled",
                    ),
                ),
                ("tracked_at", models.DateTimeField(null=True, blank=True)),
                (
                    "last_synced_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="Last third-party API sync",
                    ),
                ),
                ("metadata_json", models.JSONField(default=dict, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "voyager_keyword",
                "verbose_name": "Keyword",
                "verbose_name_plural": "Keywords",
                "ordering": ["-opportunity_score"],
                "indexes": [
                    models.Index(fields=["tenant_id", "keyword", "location"]),
                    models.Index(fields=["tenant_id", "current_position"]),
                    models.Index(fields=["tenant_id", "is_tracked"]),
                    models.Index(fields=["tenant_id", "-opportunity_score"]),
                    models.Index(fields=["cluster", "-opportunity_score"]),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["tenant_id", "keyword", "location", "language"],
                        name="%(app_label)s_keyword_tenant_kw_loc_uniq",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="OnPageAudit",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)),
                ("tenant_id", models.CharField(max_length=128, db_index=True)),
                ("url", models.URLField(max_length=2048, db_index=True, help_text="Audited URL")),
                (
                    "target_keywords_json",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Keywords targeted for this page",
                    ),
                ),
                (
                    "score",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        default=100.0,
                        help_text="SEO score 0-100",
                    ),
                ),
                (
                    "grade",
                    models.CharField(
                        max_length=1,
                        choices=Grade.choices,
                        default=Grade.A,
                        help_text="Letter grade",
                    ),
                ),
                ("title", models.TextField(blank=True, help_text="Title tag content")),
                ("title_length", models.PositiveIntegerField(default=0)),
                ("meta_description", models.TextField(blank=True)),
                ("meta_description_length", models.PositiveIntegerField(default=0)),
                ("h1", models.TextField(blank=True)),
                ("h1_count", models.PositiveIntegerField(default=0)),
                ("canonical", models.URLField(max_length=2048, blank=True)),
                ("word_count", models.PositiveIntegerField(default=0)),
                (
                    "readability_score",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                        help_text="Flesch-Kincaid score",
                    ),
                ),
                (
                    "keyword_density_json",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Keyword density percentages",
                    ),
                ),
                ("internal_links", models.PositiveIntegerField(default=0)),
                ("external_links", models.PositiveIntegerField(default=0)),
                ("images_total", models.PositiveIntegerField(default=0)),
                ("images_with_alt", models.PositiveIntegerField(default=0)),
                (
                    "schema_count",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Number of JSON-LD schema blocks",
                    ),
                ),
                ("schemas_json", models.JSONField(default=list, blank=True)),
                (
                    "issues_json",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Detected issues with severity",
                    ),
                ),
                (
                    "recommendations_json",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Generated fix recommendations",
                    ),
                ),
                ("og_tags_json", models.JSONField(default=dict, blank=True)),
                ("twitter_tags_json", models.JSONField(default=dict, blank=True)),
                (
                    "headings_json",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Extracted heading structure",
                    ),
                ),
                ("metadata_json", models.JSONField(default=dict, blank=True)),
                ("audited_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "voyager_onpage_audit",
                "verbose_name": "On-Page Audit",
                "verbose_name_plural": "On-Page Audits",
                "ordering": ["-audited_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "url"]),
                    models.Index(fields=["tenant_id", "-score"]),
                    models.Index(fields=["tenant_id", "-audited_at"]),
                ],
            },
        ),
    ]
