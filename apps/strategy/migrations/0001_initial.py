"""Initial migration for the Strategy module."""

from __future__ import annotations

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        # -------------------------------------------------------------------
        # AudiencePersona — SP-001
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="AudiencePersona",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Globally unique identifier (UUID v4)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                        max_length=128,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Persona name (e.g. 'Marketing Mary')",
                        max_length=255,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Detailed persona narrative and background",
                    ),
                ),
                (
                    "demographics",
                    models.JSONField(
                        default=dict,
                        help_text="Demographic data: ageRange, gender, locations, incomeRange, education, occupation, familyStatus, languages",
                    ),
                ),
                (
                    "psychographics",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Psychographic data: values, interests, lifestyle, personality, motivations, frustrations",
                    ),
                ),
                (
                    "pain_points",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Array of pain point strings (max 20)",
                    ),
                ),
                (
                    "content_preferences",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Content preference matrix: formats, topics, tonePreference, contentLength, visualPreference",
                    ),
                ),
                (
                    "channel_preferences",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Channel ranking array with platform, rank, engagementRate, timeSpent",
                    ),
                ),
                (
                    "data_sources",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Sources used to derive this persona",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        db_index=True,
                        default=True,
                        help_text="Whether the persona is currently active",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_audience_persona",
                "verbose_name": "Audience Persona",
                "verbose_name_plural": "Audience Personas",
                "ordering": ["-created_at"],
            },
        ),
        # -------------------------------------------------------------------
        # PersonaCampaignLink — SP-001
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="PersonaCampaignLink",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Globally unique identifier (UUID v4)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "campaign_id",
                    models.UUIDField(
                        db_index=True,
                        help_text="UUID of the linked campaign",
                    ),
                ),
                (
                    "weight",
                    models.DecimalField(
                        decimal_places=2,
                        default=0.5,
                        help_text="Influence weight: 0.0 = reference, 1.0 = primary target",
                        max_digits=3,
                    ),
                ),
                (
                    "persona",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="campaign_links",
                        to="strategy.audiencepersona",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_persona_campaign_link",
                "verbose_name": "Persona Campaign Link",
                "verbose_name_plural": "Persona Campaign Links",
                "unique_together": {("persona", "campaign_id")},
            },
        ),
        # -------------------------------------------------------------------
        # CompetitorProfile — SP-002
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="CompetitorProfile",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Globally unique identifier (UUID v4)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                        max_length=128,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Competitor company name",
                        max_length=255,
                    ),
                ),
                (
                    "website",
                    models.URLField(
                        blank=True,
                        help_text="Competitor website URL",
                    ),
                ),
                (
                    "social_profiles",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Social presence: instagram, linkedin, twitter, tiktok, youtube",
                    ),
                ),
                (
                    "scraping_config",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Scraping config: frequency, sources, settings",
                    ),
                ),
                (
                    "last_scraped_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="Timestamp of last successful data scrape",
                        null=True,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        db_index=True,
                        default=True,
                        help_text="Whether this competitor is actively tracked",
                    ),
                ),
                (
                    "swot_analysis",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Auto-generated SWOT: strengths, weaknesses, opportunities, threats",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_competitor_profile",
                "verbose_name": "Competitor Profile",
                "verbose_name_plural": "Competitor Profiles",
                "ordering": ["-created_at"],
            },
        ),
        # -------------------------------------------------------------------
        # CompetitorContent — SP-002
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="CompetitorContent",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Globally unique identifier (UUID v4)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "platform",
                    models.CharField(
                        db_index=True,
                        help_text="Source platform (e.g. 'instagram', 'linkedin')",
                        max_length=50,
                    ),
                ),
                (
                    "content_type",
                    models.CharField(
                        db_index=True,
                        help_text="Content type (e.g. 'post', 'article', 'ad')",
                        max_length=50,
                    ),
                ),
                (
                    "text",
                    models.TextField(
                        blank=True,
                        help_text="Content text body",
                    ),
                ),
                (
                    "media_urls",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Array of media URLs in the content",
                    ),
                ),
                (
                    "engagement_metrics",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Engagement data: likes, shares, comments, reach",
                    ),
                ),
                (
                    "published_at",
                    models.DateTimeField(
                        blank=True,
                        db_index=True,
                        help_text="Original publication timestamp",
                        null=True,
                    ),
                ),
                (
                    "topics",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Extracted topic tags from NLP analysis",
                    ),
                ),
                (
                    "sentiment",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Sentiment score from -1.0 to 1.0",
                        max_digits=4,
                        null=True,
                    ),
                ),
                (
                    "competitor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contents",
                        to="strategy.competitorprofile",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_competitor_content",
                "verbose_name": "Competitor Content",
                "verbose_name_plural": "Competitor Contents",
                "ordering": ["-published_at", "-created_at"],
            },
        ),
        # -------------------------------------------------------------------
        # ContentStrategy — SP-003
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="ContentStrategy",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Globally unique identifier (UUID v4)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                        max_length=128,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Strategy name",
                        max_length=255,
                    ),
                ),
                (
                    "goal",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("brand_awareness", "Brand Awareness"),
                            ("lead_generation", "Lead Generation"),
                            ("engagement", "Engagement"),
                            ("conversion", "Conversion"),
                            ("retention", "Retention"),
                        ],
                        db_index=True,
                        help_text="Primary marketing goal",
                        max_length=50,
                    ),
                ),
                (
                    "target_personas",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Array of persona UUIDs this strategy targets",
                    ),
                ),
                (
                    "topic_clusters",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Topic clusters: pillars, sub-topics, search volume, difficulty",
                    ),
                ),
                (
                    "format_mix",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Recommended format distribution per channel",
                    ),
                ),
                (
                    "channel_allocation",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Resource allocation per channel",
                    ),
                ),
                (
                    "content_pillars",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Content pillar themes with descriptions",
                    ),
                ),
                (
                    "gap_analysis",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Content gap analysis results",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_content_strategy",
                "verbose_name": "Content Strategy",
                "verbose_name_plural": "Content Strategies",
                "ordering": ["-updated_at"],
            },
        ),
        # -------------------------------------------------------------------
        # EditorialCalendar — SP-004
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="EditorialCalendar",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Globally unique identifier (UUID v4)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                        max_length=128,
                    ),
                ),
                (
                    "title",
                    models.CharField(
                        help_text="Content piece title",
                        max_length=500,
                    ),
                ),
                (
                    "content_type",
                    models.CharField(
                        choices=[
                            ("blog_post", "Blog Post"),
                            ("social_post", "Social Post"),
                            ("video", "Video"),
                            ("email", "Email"),
                            ("infographic", "Infographic"),
                            ("podcast", "Podcast"),
                            ("case_study", "Case Study"),
                            ("webinar", "Webinar"),
                            ("whitepaper", "Whitepaper"),
                            ("press_release", "Press Release"),
                        ],
                        db_index=True,
                        help_text="Type of content",
                        max_length=50,
                    ),
                ),
                (
                    "platform",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        help_text="Target platform (e.g. 'linkedin', 'instagram')",
                        max_length=50,
                    ),
                ),
                (
                    "due_date",
                    models.DateField(
                        blank=True,
                        db_index=True,
                        help_text="Internal deadline",
                        null=True,
                    ),
                ),
                (
                    "publish_date",
                    models.DateField(
                        blank=True,
                        db_index=True,
                        help_text="Scheduled publication date",
                        null=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ideation", "Ideation"),
                            ("in_creation", "In Creation"),
                            ("review", "Review"),
                            ("scheduled", "Scheduled"),
                            ("published", "Published"),
                        ],
                        db_index=True,
                        default="ideation",
                        help_text="Pipeline stage",
                        max_length=30,
                    ),
                ),
                (
                    "priority",
                    models.PositiveSmallIntegerField(
                        default=3,
                        help_text="Priority 1-5 (1 = highest, 5 = lowest)",
                    ),
                ),
                (
                    "estimated_hours",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Estimated work hours",
                        max_digits=5,
                        null=True,
                    ),
                ),
                (
                    "actual_hours",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Actual hours logged",
                        max_digits=5,
                        null=True,
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        help_text="Additional planning notes",
                    ),
                ),
                (
                    "campaign_id",
                    models.UUIDField(
                        blank=True,
                        db_index=True,
                        help_text="Linked campaign UUID",
                        null=True,
                    ),
                ),
                (
                    "assignee_id",
                    models.UUIDField(
                        blank=True,
                        db_index=True,
                        help_text="Assigned team member UUID",
                        null=True,
                    ),
                ),
                (
                    "strategy",
                    models.ForeignKey(
                        blank=True,
                        help_text="Parent content strategy",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="calendar_entries",
                        to="strategy.contentstrategy",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_editorial_calendar",
                "verbose_name": "Editorial Calendar Entry",
                "verbose_name_plural": "Editorial Calendar Entries",
                "ordering": ["publish_date", "priority"],
            },
        ),
        # -------------------------------------------------------------------
        # Objective — SP-005
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="Objective",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Globally unique identifier (UUID v4)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                        max_length=128,
                    ),
                ),
                (
                    "level",
                    models.CharField(
                        choices=[
                            ("company", "Company"),
                            ("team", "Team"),
                            ("individual", "Individual"),
                        ],
                        db_index=True,
                        help_text="Scope level",
                        max_length=20,
                    ),
                ),
                (
                    "title",
                    models.CharField(
                        help_text="Objective title",
                        max_length=500,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Detailed description",
                    ),
                ),
                (
                    "quarter",
                    models.CharField(
                        db_index=True,
                        help_text="Quarter identifier (e.g. '2026-Q2')",
                        max_length=10,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("on_track", "On Track"),
                            ("at_risk", "At Risk"),
                            ("behind", "Behind"),
                            ("achieved", "Achieved"),
                            ("missed", "Missed"),
                        ],
                        db_index=True,
                        default="on_track",
                        help_text="Current status",
                        max_length=20,
                    ),
                ),
                (
                    "progress",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Overall progress (0.0 to 1.0)",
                        max_digits=5,
                    ),
                ),
                (
                    "team_id",
                    models.UUIDField(
                        blank=True,
                        db_index=True,
                        help_text="Team UUID",
                        null=True,
                    ),
                ),
                (
                    "owner_id",
                    models.UUIDField(
                        db_index=True,
                        help_text="Objective owner UUID",
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        help_text="Parent objective for hierarchical alignment",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="children",
                        to="strategy.objective",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_okr_objective",
                "verbose_name": "OKR Objective",
                "verbose_name_plural": "OKR Objectives",
                "ordering": ["-created_at"],
            },
        ),
        # -------------------------------------------------------------------
        # KeyResult — SP-005
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="KeyResult",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Globally unique identifier (UUID v4)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "title",
                    models.CharField(
                        help_text="Key result title",
                        max_length=500,
                    ),
                ),
                (
                    "kr_type",
                    models.CharField(
                        choices=[
                            ("numeric", "Numeric"),
                            ("percentage", "Percentage"),
                            ("binary", "Binary"),
                        ],
                        db_index=True,
                        help_text="Measurement type",
                        max_length=20,
                    ),
                ),
                (
                    "target_value",
                    models.DecimalField(
                        decimal_places=4,
                        help_text="Target value to achieve",
                        max_digits=15,
                    ),
                ),
                (
                    "current_value",
                    models.DecimalField(
                        decimal_places=4,
                        default=0,
                        help_text="Current measured value",
                        max_digits=15,
                    ),
                ),
                (
                    "start_value",
                    models.DecimalField(
                        decimal_places=4,
                        default=0,
                        help_text="Starting baseline value",
                        max_digits=15,
                    ),
                ),
                (
                    "direction",
                    models.CharField(
                        choices=[
                            ("increase", "Increase"),
                            ("decrease", "Decrease"),
                        ],
                        default="increase",
                        help_text="For numeric: increase or decrease",
                        max_length=10,
                    ),
                ),
                (
                    "unit",
                    models.CharField(
                        blank=True,
                        help_text="Unit of measurement",
                        max_length=50,
                    ),
                ),
                (
                    "data_source",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Automated data source config",
                    ),
                ),
                (
                    "progress",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Computed progress (0.0 to 1.0)",
                        max_digits=5,
                    ),
                ),
                (
                    "confidence",
                    models.CharField(
                        choices=[
                            ("on_track", "On Track"),
                            ("at_risk", "At Risk"),
                        ],
                        default="on_track",
                        help_text="On-track assessment",
                        max_length=20,
                    ),
                ),
                (
                    "objective",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="key_results",
                        to="strategy.objective",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_okr_key_result",
                "verbose_name": "OKR Key Result",
                "verbose_name_plural": "OKR Key Results",
                "ordering": ["created_at"],
            },
        ),
        # -------------------------------------------------------------------
        # MarketResearch — SP-006
        # -------------------------------------------------------------------
        migrations.CreateModel(
            name="MarketResearch",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Globally unique identifier (UUID v4)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                        max_length=128,
                    ),
                ),
                (
                    "industry",
                    models.CharField(
                        db_index=True,
                        help_text="Industry or vertical researched",
                        max_length=255,
                    ),
                ),
                (
                    "trends",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Detected trends with scores and lifecycle stage",
                    ),
                ),
                (
                    "market_size",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Market sizing: TAM, SAM, SOM",
                    ),
                ),
                (
                    "audience_insights",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Audience insights",
                    ),
                ),
                (
                    "competitive_landscape",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Competitive landscape",
                    ),
                ),
                (
                    "research_date",
                    models.DateField(
                        db_index=True,
                        help_text="Date the research was conducted",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_market_research",
                "verbose_name": "Market Research",
                "verbose_name_plural": "Market Research Entries",
                "ordering": ["-research_date"],
            },
        ),
        # -------------------------------------------------------------------
        # Indexes
        # -------------------------------------------------------------------
        migrations.AddIndex(
            model_name="audiencepersona",
            index=models.Index(
                fields=["tenant_id", "is_active"],
                name="vgr_persona_tenant_active_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="audiencepersona",
            index=models.Index(
                fields=["tenant_id", "name"],
                name="vgr_persona_tenant_name_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="competitorcontent",
            index=models.Index(
                fields=["competitor", "published_at"],
                name="vgr_cmpcont_comp_pub_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="editorialcalendar",
            index=models.Index(
                fields=["tenant_id", "publish_date"],
                name="vgr_cal_tenant_date_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="editorialcalendar",
            index=models.Index(
                fields=["tenant_id", "status"],
                name="vgr_cal_tenant_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="editorialcalendar",
            index=models.Index(
                fields=["tenant_id", "assignee_id"],
                name="vgr_cal_tenant_assign_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="objective",
            index=models.Index(
                fields=["tenant_id", "quarter"],
                name="vgr_obj_tenant_qtr_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="objective",
            index=models.Index(
                fields=["tenant_id", "status"],
                name="vgr_obj_tenant_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="marketresearch",
            index=models.Index(
                fields=["tenant_id", "-research_date"],
                name="vgr_mr_tenant_date_idx",
            ),
        ),
        # Unique constraints
        migrations.AddConstraint(
            model_name="audiencepersona",
            constraint=models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="strategy_persona_tenant_name_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="competitorprofile",
            constraint=models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="strategy_competitor_tenant_name_uniq",
            ),
        ),
    ]
