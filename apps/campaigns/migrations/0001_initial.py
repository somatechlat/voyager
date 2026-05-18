# Generated initial migration for campaigns module

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("clients", "0001_initial"),
    ]

    operations = [
        # -----------------------------------------------------------------
        # Campaign
        # -----------------------------------------------------------------
        migrations.CreateModel(
            name="Campaign",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        max_length=128,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                ("name", models.CharField(max_length=255, help_text="Campaign name")),
                (
                    "description",
                    models.TextField(blank=True, help_text="Detailed campaign description"),
                ),
                (
                    "objective",
                    models.CharField(
                        choices=[
                            ("awareness", "Awareness"),
                            ("engagement", "Engagement"),
                            ("conversion", "Conversion"),
                            ("retention", "Retention"),
                        ],
                        db_index=True,
                        default="awareness",
                        max_length=20,
                        help_text="Campaign objective type",
                    ),
                ),
                (
                    "stage",
                    models.CharField(
                        choices=[
                            ("planning", "Planning"),
                            ("brief", "Brief"),
                            ("creative", "Creative"),
                            ("approval", "Approval"),
                            ("launch", "Launch"),
                            ("monitoring", "Monitoring"),
                            ("optimization", "Optimization"),
                            ("reporting", "Reporting"),
                        ],
                        db_index=True,
                        default="planning",
                        max_length=20,
                        help_text="Current lifecycle stage",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("active", "Active"),
                            ("paused", "Paused"),
                            ("completed", "Completed"),
                            ("archived", "Archived"),
                            ("cancelled", "Cancelled"),
                        ],
                        db_index=True,
                        default="draft",
                        max_length=20,
                        help_text="Campaign status",
                    ),
                ),
                (
                    "start_date",
                    models.DateField(
                        blank=True, null=True, help_text="Campaign start date"
                    ),
                ),
                (
                    "end_date",
                    models.DateField(
                        blank=True, null=True, help_text="Campaign end date"
                    ),
                ),
                (
                    "budget",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Total campaign budget",
                        max_digits=14,
                        null=True,
                    ),
                ),
                (
                    "current_spend",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Total amount spent so far",
                        max_digits=14,
                    ),
                ),
                (
                    "currency",
                    models.CharField(
                        default="USD",
                        max_length=3,
                        help_text="Three-letter currency code",
                    ),
                ),
                (
                    "pacing_type",
                    models.CharField(
                        choices=[
                            ("even", "Even"),
                            ("accelerated", "Accelerated"),
                            ("front_loaded", "Front Loaded"),
                            ("performance", "Performance"),
                        ],
                        default="even",
                        max_length=20,
                        help_text="Budget pacing algorithm",
                    ),
                ),
                (
                    "attribution_model",
                    models.CharField(
                        choices=[
                            ("first_touch", "First Touch"),
                            ("last_touch", "Last Touch"),
                            ("linear", "Linear"),
                            ("time_decay", "Time Decay"),
                        ],
                        default="last_touch",
                        max_length=20,
                        help_text="Revenue attribution model",
                    ),
                ),
                (
                    "channels",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="List of configured channel types",
                    ),
                ),
                (
                    "target_audience",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Audience targeting configuration",
                    ),
                ),
                (
                    "kpis",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Key performance indicators configuration",
                    ),
                ),
                (
                    "alerts_sent",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Tracking of budget alerts already sent",
                    ),
                ),
                (
                    "created_by",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        max_length=256,
                        help_text="User ID of the campaign creator",
                    ),
                ),
                (
                    "brief_approved",
                    models.BooleanField(
                        default=False, help_text="Whether the brief has been approved"
                    ),
                ),
                (
                    "all_creatives_approved",
                    models.BooleanField(
                        default=False,
                        help_text="Whether all creative assets are approved",
                    ),
                ),
                (
                    "approval_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("changes_requested", "Changes Requested"),
                        ],
                        default="pending",
                        max_length=20,
                        help_text="Stakeholder approval status",
                    ),
                ),
                (
                    "all_platforms_published",
                    models.BooleanField(
                        default=False,
                        help_text="Whether all platform content is live",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, help_text="Timestamp when last updated"
                    ),
                ),
                (
                    "client",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="campaigns",
                        to="clients.client",
                        help_text="The client this campaign belongs to",
                    ),
                ),
                (
                    "cloned_from",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="clones",
                        to="campaigns.campaign",
                        help_text="Original campaign if this is a clone",
                    ),
                ),
                (
                    "parent_campaign",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="child_campaigns",
                        to="campaigns.campaign",
                        help_text="Parent campaign for hierarchies",
                    ),
                ),
            ],
            options={
                "verbose_name": "Campaign",
                "verbose_name_plural": "Campaigns",
                "db_table": "voyager_campaign",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="campaign",
            index=models.Index(
                fields=["tenant_id", "stage"], name="voyager_cam_tenant__4f8fbd_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="campaign",
            index=models.Index(
                fields=["tenant_id", "status"], name="voyager_cam_tenant__5e3c0e_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="campaign",
            index=models.Index(
                fields=["tenant_id", "client", "stage"],
                name="voyager_cam_tenant__c0b2fc_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="campaign",
            index=models.Index(
                fields=["tenant_id", "start_date", "end_date"],
                name="voyager_cam_tenant__d5d7ed_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="campaign",
            index=models.Index(
                fields=["tenant_id", "objective"],
                name="voyager_cam_tenant__e8a1ab_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="campaign",
            index=models.Index(
                fields=["tenant_id", "created_by"],
                name="voyager_cam_tenant__fa2b3c_idx",
            ),
        ),
        # -----------------------------------------------------------------
        # CampaignChannel
        # -----------------------------------------------------------------
        migrations.CreateModel(
            name="CampaignChannel",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "channel_type",
                    models.CharField(
                        choices=[
                            ("organic_social", "Organic Social"),
                            ("paid_search", "Paid Search"),
                            ("paid_social", "Paid Social"),
                            ("email", "Email"),
                            ("seo", "SEO"),
                            ("influencer", "Influencer"),
                            ("display", "Display"),
                            ("video", "Video"),
                        ],
                        db_index=True,
                        max_length=30,
                        help_text="Type of marketing channel",
                    ),
                ),
                (
                    "platform",
                    models.CharField(
                        max_length=50,
                        help_text="Platform name (e.g. google_ads, meta_ads)",
                    ),
                ),
                (
                    "config",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Channel-specific configuration",
                    ),
                ),
                (
                    "daily_budget",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Daily spend limit for this channel",
                        max_digits=12,
                        null=True,
                    ),
                ),
                (
                    "total_spend",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Total spend on this channel",
                        max_digits=14,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("active", "Active"),
                            ("paused", "Paused"),
                            ("completed", "Completed"),
                            ("error", "Error"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                        help_text="Channel status",
                    ),
                ),
                (
                    "start_date",
                    models.DateField(
                        blank=True, null=True, help_text="Channel-specific start date"
                    ),
                ),
                (
                    "end_date",
                    models.DateField(
                        blank=True, null=True, help_text="Channel-specific end date"
                    ),
                ),
                (
                    "dependencies",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="List of channel IDs this channel depends on",
                    ),
                ),
                (
                    "lead_time_days",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Days needed before this channel can launch",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, help_text="Timestamp when created"
                    ),
                ),
                (
                    "campaign",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="channel_configs",
                        to="campaigns.campaign",
                        help_text="Parent campaign",
                    ),
                ),
            ],
            options={
                "verbose_name": "Campaign Channel",
                "verbose_name_plural": "Campaign Channels",
                "db_table": "voyager_campaign_channel",
                "ordering": ["channel_type", "-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="campaignchannel",
            index=models.Index(
                fields=["campaign", "channel_type"],
                name="voyager_cam_campaign__a1b2c3_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="campaignchannel",
            index=models.Index(
                fields=["campaign", "status"],
                name="voyager_cam_campaign__d4e5f6_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="campaignchannel",
            index=models.Index(
                fields=["channel_type", "platform"],
                name="voyager_cam_channel__g7h8i9_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="campaignchannel",
            constraint=models.UniqueConstraint(
                fields=["campaign", "channel_type", "platform"],
                name="campaign_channel_uniq",
            ),
        ),
        # -----------------------------------------------------------------
        # CampaignABTest
        # -----------------------------------------------------------------
        migrations.CreateModel(
            name="CampaignABTest",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=255, help_text="Test name"),
                ),
                (
                    "test_type",
                    models.CharField(
                        choices=[
                            ("subject_line", "Subject Line"),
                            ("creative", "Creative"),
                            ("landing_page", "Landing Page"),
                            ("audience", "Audience"),
                            ("bid_strategy", "Bid Strategy"),
                            ("ad_copy", "Ad Copy"),
                            ("cta", "Call to Action"),
                            ("placement", "Placement"),
                        ],
                        db_index=True,
                        max_length=30,
                        help_text="Type of element being tested",
                    ),
                ),
                (
                    "method",
                    models.CharField(
                        choices=[
                            ("frequentist", "Frequentist"),
                            ("bayesian", "Bayesian"),
                        ],
                        default="frequentist",
                        max_length=15,
                        help_text="Statistical method",
                    ),
                ),
                (
                    "significance_level",
                    models.DecimalField(
                        decimal_places=4,
                        default=0.05,
                        help_text="Alpha level (e.g. 0.05)",
                        max_digits=5,
                    ),
                ),
                (
                    "power",
                    models.DecimalField(
                        decimal_places=4,
                        default=0.8,
                        help_text="Statistical power (e.g. 0.80)",
                        max_digits=5,
                    ),
                ),
                (
                    "sample_size_per_variant",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Required sample size per variant",
                        null=True,
                    ),
                ),
                (
                    "actual_sample_size",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Actual sample size reached",
                        null=True,
                    ),
                ),
                (
                    "baseline_rate",
                    models.DecimalField(
                        blank=True,
                        decimal_places=5,
                        help_text="Baseline conversion rate (e.g. 0.05)",
                        max_digits=7,
                        null=True,
                    ),
                ),
                (
                    "minimum_detectable_effect",
                    models.DecimalField(
                        blank=True,
                        decimal_places=4,
                        help_text="Relative lift to detect (e.g. 0.20)",
                        max_digits=6,
                        null=True,
                    ),
                ),
                (
                    "daily_traffic",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Expected daily visitors",
                        null=True,
                    ),
                ),
                (
                    "estimated_duration_days",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Calculated test duration in days",
                        null=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("running", "Running"),
                            ("paused", "Paused"),
                            ("completed", "Completed"),
                            ("cancelled", "Cancelled"),
                        ],
                        db_index=True,
                        default="draft",
                        max_length=15,
                        help_text="Test lifecycle status",
                    ),
                ),
                (
                    "winner_criteria",
                    models.CharField(
                        choices=[
                            ("conversion_rate", "Conversion Rate"),
                            ("click_rate", "Click Rate"),
                            ("revenue", "Revenue"),
                            ("roas", "ROAS"),
                            ("cpa", "CPA"),
                            ("engagement", "Engagement"),
                        ],
                        default="conversion_rate",
                        max_length=20,
                        help_text="Metric for selecting winner",
                    ),
                ),
                (
                    "winner_variant_id",
                    models.CharField(
                        blank=True,
                        max_length=128,
                        help_text="ID of winning variant",
                    ),
                ),
                (
                    "variants",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Array of test variants",
                    ),
                ),
                (
                    "results",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Test results",
                    ),
                ),
                (
                    "start_date",
                    models.DateTimeField(
                        blank=True, null=True, help_text="When the test started"
                    ),
                ),
                (
                    "end_date",
                    models.DateTimeField(
                        blank=True, null=True, help_text="When the test ended"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, help_text="Timestamp when created"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, help_text="Timestamp when last updated"
                    ),
                ),
                (
                    "campaign",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ab_tests",
                        to="campaigns.campaign",
                        help_text="Parent campaign",
                    ),
                ),
            ],
            options={
                "verbose_name": "Campaign A/B Test",
                "verbose_name_plural": "Campaign A/B Tests",
                "db_table": "voyager_campaign_ab_test",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="campaignabtest",
            index=models.Index(
                fields=["campaign", "status"],
                name="voyager_abt_campaign__j1k2l3_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="campaignabtest",
            index=models.Index(
                fields=["campaign", "test_type"],
                name="voyager_abt_campaign__m4n5o6_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="campaignabtest",
            index=models.Index(
                fields=["method", "status"],
                name="voyager_abt_method__p7q8r9_idx",
            ),
        ),
        # -----------------------------------------------------------------
        # CampaignBudget
        # -----------------------------------------------------------------
        migrations.CreateModel(
            name="CampaignBudget",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Transaction amount (positive allocation, negative spend)",
                        max_digits=14,
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("allocation", "Allocation"),
                            ("spend", "Spend"),
                            ("adjustment", "Adjustment"),
                            ("refund", "Refund"),
                        ],
                        db_index=True,
                        max_length=20,
                        help_text="Type of budget entry",
                    ),
                ),
                (
                    "channel",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        max_length=50,
                        help_text="Channel reference (e.g. 'google_ads')",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True, help_text="Human-readable description"
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Additional context (roas, cpa, impressions, etc)",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when created",
                    ),
                ),
                (
                    "campaign",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="budget_entries",
                        to="campaigns.campaign",
                        help_text="Parent campaign",
                    ),
                ),
            ],
            options={
                "verbose_name": "Campaign Budget Entry",
                "verbose_name_plural": "Campaign Budget Entries",
                "db_table": "voyager_campaign_budget",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="campaignbudget",
            index=models.Index(
                fields=["campaign", "type", "-created_at"],
                name="voyager_bgt_campaign__s1t2u3_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="campaignbudget",
            index=models.Index(
                fields=["campaign", "channel", "-created_at"],
                name="voyager_bgt_campaign__v4w5x6_idx",
            ),
        ),
        # -----------------------------------------------------------------
        # CampaignPerformance
        # -----------------------------------------------------------------
        migrations.CreateModel(
            name="CampaignPerformance",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "metric_date",
                    models.DateField(
                        db_index=True, help_text="Date of the metrics"
                    ),
                ),
                (
                    "impressions",
                    models.PositiveBigIntegerField(
                        default=0, help_text="Number of impressions"
                    ),
                ),
                (
                    "clicks",
                    models.PositiveBigIntegerField(
                        default=0, help_text="Number of clicks"
                    ),
                ),
                (
                    "conversions",
                    models.PositiveBigIntegerField(
                        default=0, help_text="Number of conversions"
                    ),
                ),
                (
                    "spend",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Amount spent",
                        max_digits=14,
                    ),
                ),
                (
                    "revenue",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Revenue generated",
                        max_digits=14,
                    ),
                ),
                (
                    "engagement_actions",
                    models.PositiveBigIntegerField(
                        default=0, help_text="Engagement actions count"
                    ),
                ),
                (
                    "metrics",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Additional flexible metrics (CTR, CPC, CPA, ROAS, etc)",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, help_text="Timestamp when created"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, help_text="Timestamp when last updated"
                    ),
                ),
                (
                    "campaign",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="performance_records",
                        to="campaigns.campaign",
                        help_text="Parent campaign",
                    ),
                ),
                (
                    "channel",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="performance_records",
                        to="campaigns.campaignchannel",
                        help_text="Channel for channel-level metrics",
                    ),
                ),
            ],
            options={
                "verbose_name": "Campaign Performance",
                "verbose_name_plural": "Campaign Performances",
                "db_table": "voyager_campaign_performance",
                "ordering": ["-metric_date", "campaign"],
            },
        ),
        migrations.AddIndex(
            model_name="campaignperformance",
            index=models.Index(
                fields=["campaign", "-metric_date"],
                name="voyager_per_campaign__y7z8a1_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="campaignperformance",
            index=models.Index(
                fields=["campaign", "channel", "-metric_date"],
                name="voyager_per_campaign__b2c3d4_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="campaignperformance",
            constraint=models.UniqueConstraint(
                fields=["campaign", "channel", "metric_date"],
                name="campaign_perf_daily_uniq",
            ),
        ),
        # -----------------------------------------------------------------
        # CampaignBrief
        # -----------------------------------------------------------------
        migrations.CreateModel(
            name="CampaignBrief",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "objective_type",
                    models.CharField(
                        blank=True,
                        max_length=20,
                        help_text="Extracted campaign goal type",
                    ),
                ),
                (
                    "target_metrics",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Target KPIs and goals",
                    ),
                ),
                (
                    "selected_personas",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Top 3 matched audience personas",
                    ),
                ),
                (
                    "competitive_insights",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Competitive landscape analysis",
                    ),
                ),
                (
                    "recommended_channels",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Scored channel recommendations",
                    ),
                ),
                (
                    "estimated_timeline_days",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Suggested timeline in days",
                        null=True,
                    ),
                ),
                (
                    "suggested_budget",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="AI-suggested budget breakdown by channel",
                    ),
                ),
                (
                    "executive_summary",
                    models.TextField(
                        blank=True, help_text="Executive summary section"
                    ),
                ),
                (
                    "objectives_and_kpis",
                    models.TextField(
                        blank=True, help_text="Objectives and KPIs section"
                    ),
                ),
                (
                    "target_audience_profiles",
                    models.TextField(
                        blank=True, help_text="Target audience profiles section"
                    ),
                ),
                (
                    "channel_strategy",
                    models.TextField(
                        blank=True, help_text="Channel strategy section"
                    ),
                ),
                (
                    "content_requirements",
                    models.TextField(
                        blank=True, help_text="Content requirements section"
                    ),
                ),
                (
                    "timeline_details",
                    models.TextField(blank=True, help_text="Timeline section"),
                ),
                (
                    "budget_breakdown",
                    models.TextField(
                        blank=True, help_text="Budget breakdown section"
                    ),
                ),
                (
                    "risk_assessment",
                    models.TextField(
                        blank=True, help_text="Risk assessment section"
                    ),
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
                        blank=True,
                        max_length=256,
                        help_text="User ID who approved the brief",
                    ),
                ),
                (
                    "approved_at",
                    models.DateTimeField(
                        blank=True, null=True, help_text="When the brief was approved"
                    ),
                ),
                (
                    "version",
                    models.PositiveIntegerField(
                        default=1, help_text="Brief version number"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, help_text="Timestamp when created"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, help_text="Timestamp when last updated"
                    ),
                ),
                (
                    "campaign",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="briefs",
                        to="campaigns.campaign",
                        help_text="Parent campaign",
                    ),
                ),
            ],
            options={
                "verbose_name": "Campaign Brief",
                "verbose_name_plural": "Campaign Briefs",
                "db_table": "voyager_campaign_brief",
                "ordering": ["-version", "-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="campaignbrief",
            index=models.Index(
                fields=["campaign", "-version"],
                name="voyager_brf_campaign__e5f6g7_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="campaignbrief",
            index=models.Index(
                fields=["campaign", "is_approved"],
                name="voyager_brf_campaign__h8i9j0_idx",
            ),
        ),
    ]
