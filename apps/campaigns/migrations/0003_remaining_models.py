# Generated initial migration for campaigns


from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [("campaigns", "0002_additional_models")]

    operations = [
        migrations.CreateModel(
            name="CampaignPerformance",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "campaign",
                    models.ForeignKey(
                        Campaign,
                        on_delete=models.CASCADE,
                        related_name="performance_records",
                        help_text="Parent campaign",
                    ),
                ),
                (
                    "channel",
                    models.ForeignKey(
                        CampaignChannel,
                        on_delete=models.CASCADE,
                        null=True,
                        blank=True,
                        related_name="performance_records",
                        help_text="Channel for channel-level metrics",
                    ),
                ),
                ("metric_date", models.DateField(db_index=True, help_text="Date of the metrics")),
                (
                    "spend",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=2,
                        default=0,
                        help_text="Amount spent",
                    ),
                ),
                (
                    "revenue",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=2,
                        default=0,
                        help_text="Revenue generated",
                    ),
                ),
                (
                    "metrics",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Additional flexible metrics (CTR, CPC, CPA, ROAS, etc)",
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
                "db_table": "voyager_campaign_performance",
                "verbose_name": "Campaign Performance",
                "verbose_name_plural": "Campaign Performances",
                "ordering": ["-metric_date", "campaign"],
                "indexes": [
                    models.Index(fields=["campaign", "-metric_date"]),
                    models.Index(fields=["campaign", "channel", "-metric_date"]),
                    models.Index(fields=["metric_date"]),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["campaign", "channel", "metric_date"],
                        name="campaign_perf_daily_uniq",
                    )
                ],
            },
        ),
    ]
