"""Initial migration for the Content Creation module.

Creates all 6 core tables: content_generations, brand_kits,
content_templates, ab_tests, revision_history, and
content_repurposing_rules.
"""

from __future__ import annotations

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    """Initial migration — creates all Content Creation tables."""

    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        # -------------------------------------------------------------------
        # Base abstract models are not created — they are Python-only
        # -------------------------------------------------------------------

        # -------------------------------------------------------------------
        # BrandKit
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="BrandKit",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        help_text="Globally unique identifier (UUID v4)",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128, db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=255, help_text="Brand kit name",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True, help_text="Optional longer explanation",
                    ),
                ),
                (
                    "voice",
                    models.CharField(
                        max_length=32,
                        choices=[
                            ("professional", "Professional"),
                            ("casual", "Casual"),
                            ("friendly", "Friendly"),
                            ("humorous", "Humorous"),
                            ("urgent", "Urgent"),
                            ("inspirational", "Inspirational"),
                            ("educational", "Educational"),
                            ("provocative", "Provocative"),
                            ("empathetic", "Empathetic"),
                        ],
                        default="professional",
                        help_text="Primary voice descriptor",
                    ),
                ),
                (
                    "tone_rules",
                    models.JSONField(
                        default=list, blank=True,
                        help_text="Tone enforcement rules",
                    ),
                ),
                (
                    "forbidden_words",
                    models.JSONField(
                        default=list, blank=True,
                        help_text="Words that must not appear in content",
                    ),
                ),
                (
                    "required_phrases",
                    models.JSONField(
                        default=list, blank=True,
                        help_text="Phrases that must appear in content",
                    ),
                ),
                (
                    "color_palette",
                    models.JSONField(
                        default=list, blank=True,
                        help_text="Brand color definitions [{name, hex} ..]",
                    ),
                ),
                (
                    "logo_url",
                    models.URLField(
                        blank=True, help_text="URL to brand logo asset",
                    ),
                ),
                (
                    "font_preferences",
                    models.JSONField(
                        default=dict, blank=True,
                        help_text="Font configuration {heading, body, sizes}",
                    ),
                ),
                (
                    "competitor_list",
                    models.JSONField(
                        default=list, blank=True,
                        help_text="Competitor names to avoid mentioning",
                    ),
                ),
                (
                    "avoid_topics",
                    models.JSONField(
                        default=list, blank=True,
                        help_text="Topics to avoid in content",
                    ),
                ),
                (
                    "target_audience",
                    models.JSONField(
                        default=dict, blank=True,
                        help_text="Target audience demographics and psychographics",
                    ),
                ),
                (
                    "min_readability",
                    models.DecimalField(
                        decimal_places=2, default=60.0, max_digits=5,
                        help_text="Minimum Flesch reading ease score",
                    ),
                ),
                (
                    "min_compliance_score",
                    models.IntegerField(
                        default=75,
                        help_text="Minimum compliance score to pass (0-100)",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_brand_kit",
                "verbose_name": "Brand Kit",
                "verbose_name_plural": "Brand Kits",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="brandkit",
            index=models.Index(
                fields=["tenant_id", "name"],
                name="voyager_brandkit_tenant_name_idx",
            ),
        ),

        # -------------------------------------------------------------------
        # ContentGeneration
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="ContentGeneration",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        help_text="Globally unique identifier (UUID v4)",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128, db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "title",
                    models.CharField(
                        max_length=512,
                        help_text="Human-readable title for the generation",
                    ),
                ),
                (
                    "prompt",
                    models.TextField(
                        help_text="Raw prompt / brief submitted by the user",
                    ),
                ),
                (
                    "content_type",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("text", "Text"),
                            ("image", "Image"),
                            ("video", "Video"),
                        ],
                        db_index=True,
                        help_text="Type of content generated",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("draft", "Draft"),
                            ("generating", "Generating"),
                            ("published", "Published"),
                            ("failed", "Failed"),
                        ],
                        default="draft",
                        db_index=True,
                        help_text="Current lifecycle state",
                    ),
                ),
                (
                    "body_text",
                    models.TextField(
                        blank=True, help_text="Generated text content",
                    ),
                ),
                (
                    "media_urls",
                    models.JSONField(
                        default=list, blank=True,
                        help_text="List of URLs for generated images / videos",
                    ),
                ),
                (
                    "model_used",
                    models.CharField(
                        max_length=50, blank=True,
                        help_text="AI model that produced the content",
                    ),
                ),
                (
                    "tokens_used",
                    models.IntegerField(
                        null=True, blank=True,
                        help_text="Tokens consumed during generation",
                    ),
                ),
                (
                    "generation_time_ms",
                    models.IntegerField(
                        null=True, blank=True,
                        help_text="Wall-clock generation time in milliseconds",
                    ),
                ),
                (
                    "brand_kit_id",
                    models.UUIDField(
                        null=True, blank=True, db_index=True,
                        help_text="Brand kit applied to this generation",
                    ),
                ),
                (
                    "template_id",
                    models.UUIDField(
                        null=True, blank=True, db_index=True,
                        help_text="Template used as a base",
                    ),
                ),
                (
                    "created_by",
                    models.CharField(
                        max_length=256, db_index=True,
                        help_text="UUID of the user who initiated the generation",
                    ),
                ),
                (
                    "readability_score",
                    models.DecimalField(
                        decimal_places=2, max_digits=5,
                        null=True, blank=True,
                        help_text="Flesch-Kincaid readability score",
                    ),
                ),
                (
                    "engagement_prediction",
                    models.DecimalField(
                        decimal_places=2, max_digits=5,
                        null=True, blank=True,
                        help_text="Predicted engagement score (0-100)",
                    ),
                ),
                (
                    "brand_compliance_score",
                    models.DecimalField(
                        decimal_places=2, max_digits=5,
                        null=True, blank=True,
                        help_text="Brand compliance score (0-100)",
                    ),
                ),
                (
                    "seo_score",
                    models.DecimalField(
                        decimal_places=2, max_digits=5,
                        null=True, blank=True,
                        help_text="SEO keyword density score (0-100)",
                    ),
                ),
                (
                    "language",
                    models.CharField(
                        max_length=10, default="en",
                        help_text="ISO 639-1 language code",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_content_generation",
                "verbose_name": "Content Generation",
                "verbose_name_plural": "Content Generations",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="contentgeneration",
            index=models.Index(
                fields=["tenant_id", "status"],
                name="voyager_contentgen_tenant_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="contentgeneration",
            index=models.Index(
                fields=["tenant_id", "content_type"],
                name="voyager_contentgen_tenant_type_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="contentgeneration",
            index=models.Index(
                fields=["tenant_id", "created_by"],
                name="voyager_contentgen_tenant_user_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="contentgeneration",
            index=models.Index(
                fields=["tenant_id", "created_at"],
                name="voyager_contentgen_tenant_created_idx",
            ),
        ),

        # -------------------------------------------------------------------
        # ContentTemplate
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="ContentTemplate",
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
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, db_index=True),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128, db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=255, help_text="Template name"),
                ),
                (
                    "description",
                    models.TextField(blank=True),
                ),
                (
                    "category",
                    models.CharField(
                        max_length=32,
                        choices=[
                            ("social", "Social Media"),
                            ("blog", "Blog"),
                            ("email", "Email"),
                            ("ad", "Advertisement"),
                            ("product", "Product Description"),
                            ("newsletter", "Newsletter"),
                            ("press", "Press Release"),
                        ],
                        db_index=True,
                        help_text="Content category",
                    ),
                ),
                (
                    "content_type",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("text", "Text"),
                            ("image", "Image"),
                            ("video", "Video"),
                        ],
                        default="text",
                    ),
                ),
                (
                    "body",
                    models.TextField(help_text="Jinja2 template body"),
                ),
                (
                    "variables",
                    models.JSONField(
                        default=list, blank=True,
                        help_text="Variable definitions",
                    ),
                ),
                (
                    "default_values",
                    models.JSONField(
                        default=dict, blank=True,
                        help_text="Default values for template variables",
                    ),
                ),
                (
                    "brand_kit_id",
                    models.UUIDField(
                        null=True, blank=True,
                        help_text="Optional default brand kit",
                    ),
                ),
                (
                    "usage_count",
                    models.IntegerField(
                        default=0,
                        help_text="Number of times this template has been rendered",
                    ),
                ),
                (
                    "is_public",
                    models.BooleanField(
                        default=False,
                        help_text="System-wide public template flag",
                    ),
                ),
                (
                    "created_by",
                    models.CharField(
                        max_length=256, blank=True,
                        help_text="UUID of the user who created the template",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_content_template",
                "verbose_name": "Content Template",
                "verbose_name_plural": "Content Templates",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="contenttemplate",
            index=models.Index(
                fields=["tenant_id", "category"],
                name="voyager_template_tenant_cat_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="contenttemplate",
            index=models.Index(
                fields=["is_public"],
                name="voyager_template_public_idx",
            ),
        ),

        # -------------------------------------------------------------------
        # ABTest
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="ABTest",
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
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128, db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=255, help_text="Test name"),
                ),
                (
                    "content_generation_id",
                    models.UUIDField(
                        db_index=True,
                        help_text="Base content generation being tested",
                    ),
                ),
                (
                    "variants",
                    models.JSONField(
                        default=list, blank=True,
                        help_text="List of variant content objects",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("draft", "Draft"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("archived", "Archived"),
                        ],
                        default="draft",
                        db_index=True,
                    ),
                ),
                (
                    "start_date",
                    models.DateTimeField(null=True, blank=True),
                ),
                (
                    "end_date",
                    models.DateTimeField(null=True, blank=True),
                ),
                (
                    "sample_size",
                    models.IntegerField(
                        null=True, blank=True,
                        help_text="Target impressions per variant",
                    ),
                ),
                (
                    "winner_criteria",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("ctr", "Click-Through Rate"),
                            ("conversion", "Conversion Rate"),
                            ("engagement", "Engagement Rate"),
                        ],
                        default="ctr",
                    ),
                ),
                (
                    "results",
                    models.JSONField(
                        default=dict, blank=True,
                        help_text="Statistical results and winner information",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
            ],
            options={
                "db_table": "voyager_ab_test",
                "verbose_name": "A/B Test",
                "verbose_name_plural": "A/B Tests",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="abtest",
            index=models.Index(
                fields=["tenant_id", "status"],
                name="voyager_abtest_tenant_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="abtest",
            index=models.Index(
                fields=["tenant_id", "content_generation_id"],
                name="voyager_abtest_tenant_gen_idx",
            ),
        ),

        # -------------------------------------------------------------------
        # RevisionHistory
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="RevisionHistory",
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
                (
                    "content_generation_id",
                    models.UUIDField(
                        db_index=True,
                        help_text="Content generation being revised",
                    ),
                ),
                (
                    "version_number",
                    models.PositiveIntegerField(
                        help_text="Sequential version number",
                    ),
                ),
                (
                    "diff_json",
                    models.JSONField(
                        default=dict, blank=True,
                        help_text="Word-level diff data",
                    ),
                ),
                (
                    "body_text",
                    models.TextField(blank=True, help_text="Full text of this revision"),
                ),
                (
                    "changed_by",
                    models.CharField(
                        max_length=256,
                        help_text="UUID of the user who made the change",
                    ),
                ),
                (
                    "change_summary",
                    models.CharField(
                        max_length=512, blank=True,
                        help_text="Human-readable change summary",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
            ],
            options={
                "db_table": "voyager_revision_history",
                "verbose_name": "Revision History",
                "verbose_name_plural": "Revision Histories",
                "ordering": ["-version_number"],
            },
        ),
        migrations.AddIndex(
            model_name="revisionhistory",
            index=models.Index(
                fields=["content_generation_id", "-version_number"],
                name="voyager_rev_content_version_idx",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="revisionhistory",
            unique_together={("content_generation_id", "version_number")},
        ),

        # -------------------------------------------------------------------
        # ContentRepurposingRule
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="ContentRepurposingRule",
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
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, db_index=True),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128, db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=255, help_text="Rule name"),
                ),
                (
                    "description",
                    models.TextField(blank=True),
                ),
                (
                    "source_format",
                    models.CharField(
                        max_length=32,
                        choices=[
                            ("blog", "Blog Post"),
                            ("video", "Video"),
                            ("podcast", "Podcast"),
                            ("newsletter", "Newsletter"),
                            ("social", "Social Post"),
                            ("email", "Email"),
                        ],
                        db_index=True,
                        help_text="Input content format",
                    ),
                ),
                (
                    "target_formats",
                    models.JSONField(
                        default=list, blank=True,
                        help_text="Supported output formats",
                    ),
                ),
                (
                    "transformation_rules",
                    models.JSONField(
                        default=dict, blank=True,
                        help_text="Transformation configuration rules",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Whether the rule is currently active",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_content_repurposing_rule",
                "verbose_name": "Content Repurposing Rule",
                "verbose_name_plural": "Content Repurposing Rules",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="contentrepurposingrule",
            index=models.Index(
                fields=["tenant_id", "source_format"],
                name="voyager_reprule_tenant_source_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="contentrepurposingrule",
            index=models.Index(
                fields=["tenant_id", "is_active"],
                name="voyager_reprule_tenant_active_idx",
            ),
        ),
    ]
