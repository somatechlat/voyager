"""Migration for Social Media module (part 4).

Creates CompetitorBenchmark table.
"""

from __future__ import annotations

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    """Migration part 4 — competitor benchmarks."""

    dependencies = [
        ("social_media", "0003_influencer_mention"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompetitorBenchmark",
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
                ("competitor_name", models.CharField(blank=True, max_length=255)),
                (
                    "competitor_handle",
                    models.CharField(blank=True, db_index=True, max_length=255),
                ),
                ("competitor_avatar", models.URLField(blank=True)),
                ("metric_period", models.CharField(default="weekly", max_length=20)),
                ("period_start", models.DateField(db_index=True)),
                ("period_end", models.DateField(db_index=True)),
                ("posts_count", models.PositiveIntegerField(default=0)),
                (
                    "avg_engagement_rate",
                    models.DecimalField(
                        blank=True, decimal_places=4, max_digits=5, null=True
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
                        blank=True, decimal_places=4, max_digits=5, null=True
                    ),
                ),
                ("brand_total_followers", models.PositiveIntegerField(default=0)),
                ("brand_follower_growth", models.IntegerField(default=0)),
                (
                    "engagement_diff",
                    models.DecimalField(
                        blank=True, decimal_places=4, max_digits=6, null=True
                    ),
                ),
                ("follower_diff", models.IntegerField(default=0)),
                ("content_themes", models.JSONField(blank=True, default=list)),
            ],
            options={
                "db_table": "sm_competitor_benchmarks",
                "ordering": ["-period_end", "-engagement_diff"],
            },
        ),
        migrations.AddIndex(
            model_name="competitorbenchmark",
            index=models.Index(
                fields=["tenant_id", "competitor_handle"],
                name="sm_bench_tenant_comp",
            ),
        ),
        migrations.AddIndex(
            model_name="competitorbenchmark",
            index=models.Index(
                fields=["tenant_id", "platform", "period_end"],
                name="sm_bench_tenant_plat",
            ),
        ),
        migrations.AddIndex(
            model_name="competitorbenchmark",
            index=models.Index(
                fields=["tenant_id", "metric_period"],
                name="sm_bench_tenant_period",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="competitorbenchmark",
            unique_together={
                (
                    "tenant_id",
                    "platform",
                    "competitor_handle",
                    "metric_period",
                    "period_start",
                )
            },
        ),
    ]
