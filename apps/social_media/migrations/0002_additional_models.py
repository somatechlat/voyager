# Generated initial migration for social_media


from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [("social_media", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="HashtagResearch",
            fields=[
                ("hashtag", models.CharField(max_length=255, db_index=True)),
                ("platform", models.CharField(max_length=50, choices=PLATFORMS, db_index=True)),
                ("posts_last_week", models.PositiveIntegerField(default=0)),
                ("posts_last_day", models.PositiveIntegerField(default=0)),
                (
                    "avg_engagement",
                    models.DecimalField(
                        max_digits=10,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "top_post_min_engagement",
                    models.DecimalField(
                        max_digits=10,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "competition_score",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "opportunity_score",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "recommendation",
                    models.CharField(
                        max_length=30,
                        choices=RECOMMENDATIONS,
                        blank=True,
                        db_index=True,
                    ),
                ),
                (
                    "trend_direction",
                    models.CharField(
                        max_length=20,
                        choices=TRENDS,
                        blank=True,
                        db_index=True,
                    ),
                ),
                (
                    "trend_percentage",
                    models.DecimalField(
                        max_digits=6,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                ("related_hashtags", models.JSONField(default=list, blank=True)),
                ("category", models.CharField(max_length=255, blank=True, db_index=True)),
                ("researched_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "sm_hashtag_research",
                "ordering": ["-opportunity_score", "-posts_last_week"],
                "indexes": [
                    models.Index(fields=["tenant_id", "platform", "opportunity_score"]),
                    models.Index(fields=["tenant_id", "recommendation"]),
                    models.Index(fields=["tenant_id", "trend_direction"]),
                    models.Index(fields=["tenant_id", "hashtag", "platform"]),
                    models.Index(fields=["tenant_id", "category"]),
                ],
                "unique_together": [("tenant_id", "hashtag", "platform")],
            },
        ),
        migrations.CreateModel(
            name="InfluencerProfile",
            fields=[
                ("platform", models.CharField(max_length=50, choices=PLATFORMS, db_index=True)),
                ("platform_user_id", models.CharField(max_length=255, blank=True, db_index=True)),
                ("name", models.CharField(max_length=255, blank=True, db_index=True)),
                ("avatar", models.URLField(blank=True)),
                ("bio", models.TextField(blank=True)),
                ("followers", models.PositiveIntegerField(default=0)),
                ("following", models.PositiveIntegerField(default=0)),
                (
                    "engagement_rate",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=4,
                        null=True,
                        blank=True,
                    ),
                ),
                ("niche", models.JSONField(default=list, blank=True)),
                ("location", models.CharField(max_length=255, blank=True)),
                ("audience_demographics", models.JSONField(default=dict, blank=True)),
                (
                    "authenticity_score",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                ("red_flags", models.JSONField(default=list, blank=True)),
                (
                    "rate_estimate",
                    models.DecimalField(
                        max_digits=10,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "content_quality_score",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=STATUSES,
                        default="discovered",
                        db_index=True,
                    ),
                ),
                (
                    "outreach_status",
                    models.CharField(
                        max_length=20,
                        choices=OUTREACH_STATUSES,
                        default="not_contacted",
                        db_index=True,
                    ),
                ),
                ("outreach_sent_at", models.DateTimeField(null=True, blank=True)),
                ("responded_at", models.DateTimeField(null=True, blank=True)),
                ("notes", models.TextField(blank=True)),
                (
                    "match_score",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                        db_index=True,
                    ),
                ),
                ("contact_email", models.EmailField(blank=True)),
                ("website", models.URLField(blank=True)),
            ],
            options={
                "db_table": "sm_influencer_profiles",
                "ordering": ["-match_score", "-engagement_rate"],
                "indexes": [
                    models.Index(fields=["tenant_id", "status"]),
                    models.Index(fields=["tenant_id", "outreach_status"]),
                    models.Index(fields=["tenant_id", "platform", "niche"]),
                    models.Index(fields=["tenant_id", "authenticity_score"]),
                    models.Index(fields=["tenant_id", "match_score"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="SocialMention",
            fields=[
                ("platform", models.CharField(max_length=50, choices=PLATFORMS, db_index=True)),
                (
                    "platform_mention_id",
                    models.CharField(max_length=255, blank=True, db_index=True),
                ),
                (
                    "mention_type",
                    models.CharField(max_length=20, choices=MENTION_TYPES, db_index=True),
                ),
                ("tracked_term", models.CharField(max_length=255, db_index=True)),
                ("author_name", models.CharField(max_length=255, blank=True)),
                ("author_platform_id", models.CharField(max_length=255, blank=True)),
                ("author_avatar", models.URLField(blank=True)),
                ("author_followers", models.PositiveIntegerField(default=0)),
                ("text", models.TextField(blank=True)),
                ("url", models.URLField(blank=True)),
                (
                    "sentiment",
                    models.CharField(
                        max_length=20,
                        choices=SENTIMENTS,
                        blank=True,
                        db_index=True,
                    ),
                ),
                (
                    "sentiment_score",
                    models.DecimalField(
                        max_digits=4,
                        decimal_places=3,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "influence_score",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=2,
                        null=True,
                        blank=True,
                    ),
                ),
                ("reach_estimate", models.PositiveIntegerField(default=0)),
                ("language", models.CharField(max_length=10, blank=True)),
                ("media_urls", models.JSONField(default=list, blank=True)),
                ("is_alert_triggered", models.BooleanField(default=False, db_index=True)),
                ("alert_reason", models.TextField(blank=True)),
                ("processed", models.BooleanField(default=False, db_index=True)),
                ("mentioned_at", models.DateTimeField(db_index=True)),
            ],
            options={
                "db_table": "sm_social_mentions",
                "ordering": ["-mentioned_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "tracked_term", "mentioned_at"]),
                    models.Index(fields=["tenant_id", "sentiment", "mentioned_at"]),
                    models.Index(fields=["tenant_id", "platform", "mentioned_at"]),
                    models.Index(fields=["tenant_id", "is_alert_triggered"]),
                    models.Index(fields=["tenant_id", "mention_type"]),
                    models.Index(fields=["tenant_id", "processed"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="CompetitorBenchmark",
            fields=[
                ("platform", models.CharField(max_length=50, choices=PLATFORMS, db_index=True)),
                ("competitor_name", models.CharField(max_length=255, blank=True)),
                ("competitor_handle", models.CharField(max_length=255, blank=True, db_index=True)),
                ("competitor_avatar", models.URLField(blank=True)),
                (
                    "metric_period",
                    models.CharField(
                        max_length=20,
                        choices=METRIC_PERIODS,
                        default="weekly",
                    ),
                ),
                ("period_start", models.DateField(db_index=True)),
                ("period_end", models.DateField(db_index=True)),
                ("posts_count", models.PositiveIntegerField(default=0)),
                (
                    "avg_engagement_rate",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=4,
                        null=True,
                        blank=True,
                    ),
                ),
                ("avg_likes", models.PositiveIntegerField(default=0)),
                ("avg_comments", models.PositiveIntegerField(default=0)),
                ("avg_shares", models.PositiveIntegerField(default=0)),
                ("total_followers", models.PositiveIntegerField(default=0)),
                ("follower_growth", models.IntegerField(default=0)),
                ("top_post_url", models.URLField(blank=True)),
                ("top_post_engagement", models.PositiveIntegerField(default=0)),
                ("brand_posts_count", models.PositiveIntegerField(default=0)),
                (
                    "brand_avg_engagement",
                    models.DecimalField(
                        max_digits=5,
                        decimal_places=4,
                        null=True,
                        blank=True,
                    ),
                ),
                ("brand_total_followers", models.PositiveIntegerField(default=0)),
                ("brand_follower_growth", models.IntegerField(default=0)),
                (
                    "engagement_diff",
                    models.DecimalField(
                        max_digits=6,
                        decimal_places=4,
                        null=True,
                        blank=True,
                    ),
                ),
                ("follower_diff", models.IntegerField(default=0)),
                ("content_themes", models.JSONField(default=list, blank=True)),
            ],
            options={
                "db_table": "sm_competitor_benchmarks",
                "ordering": ["-period_end", "-engagement_diff"],
                "indexes": [
                    models.Index(fields=["tenant_id", "competitor_handle"]),
                    models.Index(fields=["tenant_id", "platform", "period_end"]),
                    models.Index(fields=["tenant_id", "metric_period"]),
                ],
                "unique_together": [
                    ("tenant_id", "platform", "competitor_handle", "metric_period", "period_start")
                ],
            },
        ),
    ]
