# Generated initial migration for campaigns


from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [("campaigns", "0003_remaining_models")]

    operations = [
        migrations.CreateModel(
            name="CampaignBrief",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "campaign",
                    models.ForeignKey(
                        Campaign,
                        on_delete=models.CASCADE,
                        related_name="briefs",
                        help_text="Parent campaign",
                    ),
                ),
                (
                    "objective_type",
                    models.CharField(
                        max_length=20,
                        blank=True,
                        help_text="Extracted campaign goal type",
                    ),
                ),
                (
                    "target_metrics",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Target KPIs and goals",
                    ),
                ),
                (
                    "selected_personas",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Top 3 matched audience personas with justification",
                    ),
                ),
                (
                    "competitive_insights",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Competitive landscape analysis",
                    ),
                ),
                (
                    "recommended_channels",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="Scored channel recommendations",
                    ),
                ),
                (
                    "estimated_timeline_days",
                    models.PositiveIntegerField(
                        null=True,
                        blank=True,
                        help_text="Suggested timeline in days",
                    ),
                ),
                (
                    "suggested_budget",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="AI-suggested budget breakdown by channel",
                    ),
                ),
                (
                    "executive_summary",
                    models.TextField(
                        blank=True,
                        help_text="Executive summary section",
                    ),
                ),
                (
                    "objectives_and_kpis",
                    models.TextField(
                        blank=True,
                        help_text="Objectives and KPIs section",
                    ),
                ),
                (
                    "target_audience_profiles",
                    models.TextField(
                        blank=True,
                        help_text="Target audience profiles section",
                    ),
                ),
                (
                    "channel_strategy",
                    models.TextField(
                        blank=True,
                        help_text="Channel strategy section",
                    ),
                ),
                (
                    "content_requirements",
                    models.TextField(
                        blank=True,
                        help_text="Content requirements section",
                    ),
                ),
                ("timeline_details", models.TextField(blank=True, help_text="Timeline section")),
                (
                    "budget_breakdown",
                    models.TextField(
                        blank=True,
                        help_text="Budget breakdown section",
                    ),
                ),
                (
                    "risk_assessment",
                    models.TextField(blank=True, help_text="Risk assessment section"),
                ),
                (
                    "raw_response",
                    models.TextField(
                        blank=True,
                        help_text="Full raw AI response for debugging",
                    ),
                ),
                (
                    "is_approved",
                    models.BooleanField(
                        default=False,
                        help_text="Whether the brief has been approved",
                    ),
                ),
                (
                    "approved_by",
                    models.CharField(
                        max_length=256,
                        blank=True,
                        help_text="User ID who approved the brief",
                    ),
                ),
                (
                    "approved_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When the brief was approved",
                    ),
                ),
                (
                    "version",
                    models.PositiveIntegerField(default=1, help_text="Brief version number"),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Timestamp when last updated",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_campaign_brief",
                "verbose_name": "Campaign Brief",
                "verbose_name_plural": "Campaign Briefs",
                "ordering": ["-version", "-created_at"],
                "indexes": [
                    models.Index(fields=["campaign", "-version"]),
                    models.Index(fields=["campaign", "is_approved"]),
                ],
            },
        ),
    ]
