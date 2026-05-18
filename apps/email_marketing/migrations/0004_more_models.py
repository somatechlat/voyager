# Generated initial migration for email_marketing


from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [("email_marketing", "0003_remaining_models")]

    operations = [
        migrations.CreateModel(
            name="EmailAnalytics",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "campaign",
                    models.OneToOneField(
                        EmailCampaign,
                        on_delete=models.CASCADE,
                        related_name="analytics",
                        help_text="The campaign these analytics belong to",
                    ),
                ),
                ("sent", models.PositiveIntegerField(default=0, help_text="Total emails sent")),
                (
                    "delivered",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Total emails delivered",
                    ),
                ),
                ("opens", models.PositiveIntegerField(default=0, help_text="Total opens")),
                ("unique_opens", models.PositiveIntegerField(default=0, help_text="Unique opens")),
                ("clicks", models.PositiveIntegerField(default=0, help_text="Total clicks")),
                (
                    "unique_clicks",
                    models.PositiveIntegerField(default=0, help_text="Unique clicks"),
                ),
                ("bounces", models.PositiveIntegerField(default=0, help_text="Total bounces")),
                ("hard_bounces", models.PositiveIntegerField(default=0, help_text="Hard bounces")),
                ("soft_bounces", models.PositiveIntegerField(default=0, help_text="Soft bounces")),
                (
                    "spam_complaints",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Spam complaints",
                    ),
                ),
                ("unsubscribes", models.PositiveIntegerField(default=0, help_text="Unsubscribes")),
                (
                    "revenue",
                    models.DecimalField(
                        max_digits=12,
                        decimal_places=2,
                        default=0.0,
                        help_text="Revenue attributed",
                    ),
                ),
                (
                    "conversions",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Number of conversions",
                    ),
                ),
                (
                    "click_heatmap",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Click heatmap data per block",
                    ),
                ),
                (
                    "device_breakdown",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Device and platform statistics",
                    ),
                ),
                (
                    "geographic_breakdown",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Geographic statistics",
                    ),
                ),
                (
                    "hourly_opens",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Opens per hour",
                    ),
                ),
                (
                    "hourly_clicks",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Clicks per hour",
                    ),
                ),
                (
                    "time_to_first_open_seconds",
                    models.PositiveIntegerField(
                        null=True,
                        blank=True,
                        help_text="Average time to first open in seconds",
                    ),
                ),
                (
                    "time_to_first_click_seconds",
                    models.PositiveIntegerField(
                        null=True,
                        blank=True,
                        help_text="Average time to first click in seconds",
                    ),
                ),
                (
                    "forward_count",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Number of forwards",
                    ),
                ),
                (
                    "print_count",
                    models.PositiveIntegerField(default=0, help_text="Number of prints"),
                ),
                (
                    "engagement_tiers",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Engagement distribution (top 10%, 25%, etc.)",
                    ),
                ),
                (
                    "calculated_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="When analytics were last calculated",
                    ),
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
                "db_table": "voyager_email_analytics",
                "verbose_name": "Email Analytics",
                "verbose_name_plural": "Email Analytics",
                "ordering": ["-calculated_at", "-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "campaign"]),
                    models.Index(fields=["tenant_id", "calculated_at"]),
                ],
            },
        ),
    ]
