"""Migration for Social Media module (part 3).

Creates InfluencerProfile and SocialMention tables.
"""

from __future__ import annotations

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    """Migration part 3 — influencers and mentions."""

    dependencies = [
        ("social_media", "0002_community_hashtag"),
    ]

    operations = [
        migrations.CreateModel(
            name="InfluencerProfile",
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
                ("platform", models.CharField(db_index=True, max_length=50)),
                (
                    "platform_user_id",
                    models.CharField(blank=True, db_index=True, max_length=255),
                ),
                ("name", models.CharField(blank=True, db_index=True, max_length=255)),
                ("avatar", models.URLField(blank=True)),
                ("bio", models.TextField(blank=True)),
                ("followers", models.PositiveIntegerField(default=0)),
                ("following", models.PositiveIntegerField(default=0)),
                (
                    "engagement_rate",
                    models.DecimalField(
                        blank=True, decimal_places=4, max_digits=5, null=True
                    ),
                ),
                ("niche", models.JSONField(blank=True, default=list)),
                ("location", models.CharField(blank=True, max_length=255)),
                ("audience_demographics", models.JSONField(blank=True, default=dict)),
                (
                    "authenticity_score",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=5, null=True
                    ),
                ),
                ("red_flags", models.JSONField(blank=True, default=list)),
                (
                    "rate_estimate",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                (
                    "content_quality_score",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=5, null=True
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        db_index=True, default="discovered", max_length=20
                    ),
                ),
                (
                    "outreach_status",
                    models.CharField(
                        db_index=True, default="not_contacted", max_length=20
                    ),
                ),
                ("outreach_sent_at", models.DateTimeField(blank=True, null=True)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                (
                    "match_score",
                    models.DecimalField(
                        blank=True,
                        db_index=True,
                        decimal_places=2,
                        max_digits=5,
                        null=True,
                    ),
                ),
                ("contact_email", models.EmailField(blank=True, max_length=254)),
                ("website", models.URLField(blank=True)),
            ],
            options={
                "db_table": "sm_influencer_profiles",
                "ordering": ["-match_score", "-engagement_rate"],
            },
        ),
        migrations.AddIndex(
            model_name="influencerprofile",
            index=models.Index(
                fields=["tenant_id", "status"], name="sm_inf_tenant_status"
            ),
        ),
        migrations.AddIndex(
            model_name="influencerprofile",
            index=models.Index(
                fields=["tenant_id", "outreach_status"],
                name="sm_inf_tenant_outreach",
            ),
        ),
        migrations.AddIndex(
            model_name="influencerprofile",
            index=models.Index(
                fields=["tenant_id", "authenticity_score"],
                name="sm_inf_tenant_auth",
            ),
        ),
        migrations.CreateModel(
            name="SocialMention",
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
                ("platform", models.CharField(db_index=True, max_length=50)),
                (
                    "platform_mention_id",
                    models.CharField(blank=True, db_index=True, max_length=255),
                ),
                ("mention_type", models.CharField(db_index=True, max_length=20)),
                ("tracked_term", models.CharField(db_index=True, max_length=255)),
                ("author_name", models.CharField(blank=True, max_length=255)),
                ("author_platform_id", models.CharField(blank=True, max_length=255)),
                ("author_avatar", models.URLField(blank=True)),
                ("author_followers", models.PositiveIntegerField(default=0)),
                ("text", models.TextField(blank=True)),
                ("url", models.URLField(blank=True)),
                (
                    "sentiment",
                    models.CharField(blank=True, db_index=True, max_length=20),
                ),
                (
                    "sentiment_score",
                    models.DecimalField(
                        blank=True, decimal_places=3, max_digits=4, null=True
                    ),
                ),
                (
                    "influence_score",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=5, null=True
                    ),
                ),
                ("reach_estimate", models.PositiveIntegerField(default=0)),
                ("language", models.CharField(blank=True, max_length=10)),
                ("media_urls", models.JSONField(blank=True, default=list)),
                (
                    "is_alert_triggered",
                    models.BooleanField(db_index=True, default=False),
                ),
                ("alert_reason", models.TextField(blank=True)),
                ("processed", models.BooleanField(db_index=True, default=False)),
                ("mentioned_at", models.DateTimeField(db_index=True)),
            ],
            options={
                "db_table": "sm_social_mentions",
                "ordering": ["-mentioned_at"],
            },
        ),
        migrations.AddIndex(
            model_name="socialmention",
            index=models.Index(
                fields=["tenant_id", "tracked_term", "mentioned_at"],
                name="sm_ment_tenant_term",
            ),
        ),
        migrations.AddIndex(
            model_name="socialmention",
            index=models.Index(
                fields=["tenant_id", "sentiment", "mentioned_at"],
                name="sm_ment_tenant_sent",
            ),
        ),
        migrations.AddIndex(
            model_name="socialmention",
            index=models.Index(
                fields=["tenant_id", "platform", "mentioned_at"],
                name="sm_ment_tenant_plat",
            ),
        ),
        migrations.AddIndex(
            model_name="socialmention",
            index=models.Index(
                fields=["tenant_id", "is_alert_triggered"],
                name="sm_ment_tenant_alert",
            ),
        ),
    ]
