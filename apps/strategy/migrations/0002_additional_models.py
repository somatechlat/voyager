# Generated initial migration for strategy


from django.db import migrations, models


class ContentType(models.TextChoices):
    BLOG_POST = "blog_post", "Blog Post"
    SOCIAL_POST = "social_post", "Social Post"
    VIDEO = "video", "Video"
    EMAIL = "email", "Email"
    INFOGRAPHIC = "infographic", "Infographic"
    PODCAST = "podcast", "Podcast"
    CASE_STUDY = "case_study", "Case Study"
    WEBINAR = "webinar", "Webinar"
    WHITEPAPER = "whitepaper", "Whitepaper"
    PRESS_RELEASE = "press_release", "Press Release"


class Goal(models.TextChoices):
    BRAND_AWARENESS = "brand_awareness", "Brand Awareness"
    LEAD_GENERATION = "lead_generation", "Lead Generation"
    ENGAGEMENT = "engagement", "Engagement"
    CONVERSION = "conversion", "Conversion"
    RETENTION = "retention", "Retention"


class Status(models.TextChoices):
    IDEATION = "ideation", "Ideation"
    IN_CREATION = "in_creation", "In Creation"
    REVIEW = "review", "Review"
    SCHEDULED = "scheduled", "Scheduled"
    PUBLISHED = "published", "Published"


class Migration(migrations.Migration):

    initial = True

    dependencies = [("strategy", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="CompetitorContent",
            fields=[
                (
                    "competitor",
                    models.ForeignKey(
                        CompetitorProfile,
                        on_delete=models.CASCADE,
                        related_name="contents",
                        help_text="The competitor who published this content",
                    ),
                ),
                (
                    "platform",
                    models.CharField(
                        max_length=50,
                        db_index=True,
                        help_text="Source platform (e.g. 'instagram', 'linkedin')",
                    ),
                ),
                (
                    "content_type",
                    models.CharField(
                        max_length=50,
                        db_index=True,
                        help_text="Content type (e.g. 'post', 'article', 'ad')",
                    ),
                ),
                ("text", models.TextField(blank=True, help_text="Content text body")),
                (
                    "media_urls",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Array of media URLs in the content",
                    ),
                ),
                (
                    "engagement_metrics",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Engagement data: likes, shares, comments, reach",
                    ),
                ),
                (
                    "published_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        db_index=True,
                        help_text="Original publication timestamp",
                    ),
                ),
                (
                    "topics",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Extracted topic tags from NLP analysis",
                    ),
                ),
                (
                    "sentiment",
                    models.DecimalField(
                        max_digits=4,
                        decimal_places=2,
                        null=True,
                        blank=True,
                        help_text="Sentiment score from -1.0 (negative) to 1.0 (positive)",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_competitor_content",
                "verbose_name": "Competitor Content",
                "verbose_name_plural": "Competitor Contents",
                "ordering": ["-published_at", "-created_at"],
                "indexes": [
                    models.Index(fields=["competitor", "platform"]),
                    models.Index(fields=["competitor", "published_at"]),
                    models.Index(fields=["competitor", "topics"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="ContentStrategy",
            fields=[
                ("name", models.CharField(max_length=255, help_text="Strategy name")),
                (
                    "goal",
                    models.CharField(
                        max_length=50,
                        choices=Goal.choices,
                        blank=True,
                        db_index=True,
                        help_text="Primary marketing goal",
                    ),
                ),
                (
                    "target_personas",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Array of persona UUIDs this strategy targets",
                    ),
                ),
                (
                    "topic_clusters",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Topic clusters: pillars, sub-topics, search volume, difficulty",
                    ),
                ),
                (
                    "format_mix",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Recommended format distribution per channel with weights",
                    ),
                ),
                (
                    "channel_allocation",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Resource allocation per channel: budget, effort, priority",
                    ),
                ),
                (
                    "content_pillars",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Content pillar themes with descriptions and target keywords",
                    ),
                ),
                (
                    "gap_analysis",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Content gap analysis: missing topics, competitor coverage, opportunity score",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_content_strategy",
                "verbose_name": "Content Strategy",
                "verbose_name_plural": "Content Strategies",
                "ordering": ["-updated_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "goal"]),
                    models.Index(fields=["tenant_id", "-updated_at"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="EditorialCalendar",
            fields=[
                ("title", models.CharField(max_length=500, help_text="Content piece title")),
                (
                    "content_type",
                    models.CharField(
                        max_length=50,
                        choices=ContentType.choices,
                        db_index=True,
                        help_text="Type of content",
                    ),
                ),
                (
                    "platform",
                    models.CharField(
                        max_length=50,
                        blank=True,
                        db_index=True,
                        help_text="Target platform (e.g. 'linkedin', 'instagram')",
                    ),
                ),
                (
                    "strategy",
                    models.ForeignKey(
                        to="strategy.ContentStrategy",
                        on_delete=models.SET_NULL,
                        null=True,
                        blank=True,
                        related_name="calendar_entries",
                        help_text="Parent content strategy",
                    ),
                ),
                (
                    "campaign_id",
                    models.UUIDField(
                        null=True,
                        blank=True,
                        db_index=True,
                        help_text="Linked campaign UUID",
                    ),
                ),
                (
                    "assignee_id",
                    models.UUIDField(
                        null=True,
                        blank=True,
                        db_index=True,
                        help_text="Assigned team member UUID",
                    ),
                ),
                (
                    "due_date",
                    models.DateField(
                        null=True,
                        blank=True,
                        db_index=True,
                        help_text="Internal deadline",
                    ),
                ),
                (
                    "publish_date",
                    models.DateField(
                        null=True,
                        blank=True,
                        db_index=True,
                        help_text="Scheduled publication date",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=30,
                        choices=Status.choices,
                        default=Status.IDEATION,
                        db_index=True,
                        help_text="Pipeline stage",
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
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                        help_text="Estimated work hours",
                    ),
                ),
                (
                    "actual_hours",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                        help_text="Actual hours logged",
                    ),
                ),
                ("notes", models.TextField(blank=True, help_text="Additional planning notes")),
            ],
            options={
                "db_table": "voyager_editorial_calendar",
                "verbose_name": "Editorial Calendar Entry",
                "verbose_name_plural": "Editorial Calendar Entries",
                "ordering": ["publish_date", "priority"],
                "indexes": [
                    models.Index(fields=["tenant_id", "publish_date"]),
                    models.Index(fields=["tenant_id", "status"]),
                    models.Index(fields=["tenant_id", "assignee_id"]),
                    models.Index(fields=["tenant_id", "content_type"]),
                    models.Index(fields=["tenant_id", "campaign_id"]),
                    models.Index(fields=["tenant_id", "due_date"]),
                    models.Index(fields=["tenant_id", "priority"]),
                ],
            },
        ),
    ]
