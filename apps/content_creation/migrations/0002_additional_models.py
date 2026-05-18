# Generated initial migration for content_creation


from django.db import migrations, models


class SourceFormat(models.TextChoices):
    BLOG = "blog", "Blog Post"
    VIDEO = "video", "Video"
    PODCAST = "podcast", "Podcast"
    NEWSLETTER = "newsletter", "Newsletter"
    SOCIAL = "social", "Social Post"
    EMAIL = "email", "Email"


class Status(models.TextChoices):
    DRAFT = "draft", "Draft"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    ARCHIVED = "archived", "Archived"


class WinnerCriteria(models.TextChoices):
    CTR = "ctr", "Click-Through Rate"
    CONVERSION = "conversion", "Conversion Rate"
    ENGAGEMENT = "engagement", "Engagement Rate"


class Migration(migrations.Migration):

    initial = True

    dependencies = [("content_creation", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="ABTest",
            fields=[
                ("name", models.CharField(max_length=255, help_text="Human-readable test name")),
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
                        default=list,
                        blank=True,
                        help_text="List of variant content objects",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.DRAFT,
                        db_index=True,
                        help_text="Current test lifecycle state",
                    ),
                ),
                (
                    "start_date",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When the test started",
                    ),
                ),
                (
                    "end_date",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When the test ended / will end",
                    ),
                ),
                (
                    "sample_size",
                    models.IntegerField(
                        null=True,
                        blank=True,
                        help_text="Target impressions per variant",
                    ),
                ),
                (
                    "winner_criteria",
                    models.CharField(
                        max_length=20,
                        choices=WinnerCriteria.choices,
                        default=WinnerCriteria.CTR,
                        help_text="Metric used to select the winner",
                    ),
                ),
                (
                    "results",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Statistical results and winner information",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the test was created",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_ab_test",
                "verbose_name": "A/B Test",
                "verbose_name_plural": "A/B Tests",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "status"]),
                    models.Index(fields=["tenant_id", "content_generation_id"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="RevisionHistory",
            fields=[
                (
                    "content_generation_id",
                    models.UUIDField(
                        db_index=True,
                        help_text="Content generation being revised",
                    ),
                ),
                (
                    "version_number",
                    models.PositiveIntegerField(help_text="Sequential version number"),
                ),
                (
                    "diff_json",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Word-level diff {additions, deletions, modifications, summary}",
                    ),
                ),
                ("body_text", models.TextField(blank=True, help_text="Full text of this revision")),
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
                        max_length=512,
                        blank=True,
                        help_text="Human-readable change summary",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the revision was created",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_revision_history",
                "verbose_name": "Revision History",
                "verbose_name_plural": "Revision Histories",
                "ordering": ["-version_number"],
                "indexes": [models.Index(fields=["content_generation_id", "-version_number"])],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["content_generation_id", "version_number"],
                        name="%(app_label)s_rev_content_version_uniq",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="ContentRepurposingRule",
            fields=[
                ("name", models.CharField(max_length=255, help_text="Human-readable rule name")),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Optional explanation of the transformation",
                    ),
                ),
                (
                    "source_format",
                    models.CharField(
                        max_length=32,
                        choices=SourceFormat.choices,
                        db_index=True,
                        help_text="Input content format",
                    ),
                ),
                (
                    "target_formats",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Supported output formats [twitter, linkedin, instagram, ...]",
                    ),
                ),
                (
                    "transformation_rules",
                    models.JSONField(
                        default=dict,
                        blank=True,
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
                "indexes": [
                    models.Index(fields=["tenant_id", "source_format"]),
                    models.Index(fields=["tenant_id", "is_active"]),
                ],
            },
        ),
    ]
