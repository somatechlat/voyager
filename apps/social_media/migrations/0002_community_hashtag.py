"""Migration for Social Media module (part 2).

Creates CommunityMember and HashtagResearch tables.
"""

from __future__ import annotations

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    """Migration part 2 — community and hashtags."""

    dependencies = [
        ("social_media", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CommunityMember",
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
                    "engagement_score",
                    models.DecimalField(
                        db_index=True, decimal_places=2, default=0, max_digits=8
                    ),
                ),
                (
                    "influence_score",
                    models.DecimalField(
                        decimal_places=2, default=0, max_digits=8
                    ),
                ),
                (
                    "loyalty_score",
                    models.DecimalField(
                        decimal_places=2, default=0, max_digits=8
                    ),
                ),
                (
                    "vip_score",
                    models.DecimalField(
                        db_index=True, decimal_places=2, default=0, max_digits=8
                    ),
                ),
                (
                    "tier",
                    models.CharField(
                        db_index=True, default="passive", max_length=20
                    ),
                ),
                ("first_seen_at", models.DateTimeField(auto_now_add=True)),
                ("last_active_at", models.DateTimeField(auto_now=True)),
                ("total_interactions", models.PositiveIntegerField(default=0)),
                ("interaction_breakdown", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "db_table": "sm_community_members",
                "ordering": ["-vip_score", "-engagement_score"],
            },
        ),
        migrations.AddIndex(
            model_name="communitymember",
            index=models.Index(
                fields=["tenant_id", "vip_score"], name="sm_comm_tenant_vip"
            ),
        ),
        migrations.AddIndex(
            model_name="communitymember",
            index=models.Index(
                fields=["tenant_id", "tier"], name="sm_comm_tenant_tier"
            ),
        ),
        migrations.AddIndex(
            model_name="communitymember",
            index=models.Index(
                fields=["tenant_id", "platform", "vip_score"],
                name="sm_comm_tenant_plat_vip",
            ),
        ),
        migrations.AddIndex(
            model_name="communitymember",
            index=models.Index(
                fields=["tenant_id", "engagement_score"],
                name="sm_comm_tenant_eng",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="communitymember",
            unique_together={("tenant_id", "platform", "platform_user_id")},
        ),
        migrations.CreateModel(
            name="HashtagResearch",
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
                ("hashtag", models.CharField(db_index=True, max_length=255)),
                ("platform", models.CharField(db_index=True, max_length=50)),
                ("total_posts", models.PositiveBigIntegerField(default=0)),
                ("posts_last_week", models.PositiveIntegerField(default=0)),
                ("posts_last_day", models.PositiveIntegerField(default=0)),
                (
                    "avg_engagement",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                (
                    "top_post_min_engagement",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                (
                    "competition_score",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=5, null=True
                    ),
                ),
                (
                    "opportunity_score",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=5, null=True
                    ),
                ),
                (
                    "recommendation",
                    models.CharField(blank=True, db_index=True, max_length=30),
                ),
                (
                    "trend_direction",
                    models.CharField(blank=True, db_index=True, max_length=20),
                ),
                (
                    "trend_percentage",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=6, null=True
                    ),
                ),
                ("related_hashtags", models.JSONField(blank=True, default=list)),
                (
                    "category",
                    models.CharField(blank=True, db_index=True, max_length=255),
                ),
                ("researched_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "sm_hashtag_research",
                "ordering": ["-opportunity_score", "-posts_last_week"],
            },
        ),
        migrations.AddIndex(
            model_name="hashtagresearch",
            index=models.Index(
                fields=["tenant_id", "platform", "opportunity_score"],
                name="sm_ht_tenant_plat_opp",
            ),
        ),
        migrations.AddIndex(
            model_name="hashtagresearch",
            index=models.Index(
                fields=["tenant_id", "recommendation"], name="sm_ht_tenant_rec"
            ),
        ),
        migrations.AddIndex(
            model_name="hashtagresearch",
            index=models.Index(
                fields=["tenant_id", "trend_direction"], name="sm_ht_tenant_trend"
            ),
        ),
        migrations.AlterUniqueTogether(
            name="hashtagresearch",
            unique_together={("tenant_id", "hashtag", "platform")},
        ),
    ]
