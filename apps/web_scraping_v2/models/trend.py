"""TrendDetection model — trend scoring with velocity and acceleration."""

from __future__ import annotations

import uuid

from django.db import models


class TrendDetection(models.Model):
    """A detected trend with scoring metrics.

    Uses velocity (rate of change) and acceleration (rate of change of
    rate of change) to classify trends into lifecycle stages.

    Attributes:
        id: UUID primary key.
        tenant_id: Tenant scope identifier.
        topic: The trending topic or keyword.
        source: Data source (e.g., twitter, reddit, news, search).
        mention_count: Total mentions in the period.
        trend_score: Composite score (0-100) weighted by volume, velocity, acceleration.
        velocity: Rate of change in mentions.
        acceleration: Rate of change of velocity.
        stage: Lifecycle stage classification.
        peak_date: Estimated peak date for the trend.
        estimated_lifespan_days: Estimated remaining lifespan in days.
        industry_baseline: Baseline mention count for the industry.
        data_points: JSON array of daily mention counts for charting.
        tracked_at: When the trend was recorded.
        created_at: Record creation timestamp.
    """

    class Stage(models.TextChoices):
        EMERGING = "emerging", "Emerging"
        PEAKING = "peaking", "Peaking"
        DECLINING = "declining", "Declining"
        RECOVERING = "recovering", "Recovering"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    topic = models.CharField(max_length=500, db_index=True)
    source = models.CharField(max_length=50, db_index=True)
    mention_count = models.PositiveIntegerField(default=0)
    trend_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    velocity = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    acceleration = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    stage = models.CharField(
        max_length=20,
        choices=Stage.choices,
        default=Stage.EMERGING,
        db_index=True,
    )
    peak_date = models.DateTimeField(null=True, blank=True)
    estimated_lifespan_days = models.PositiveIntegerField(null=True, blank=True)
    industry_baseline = models.PositiveIntegerField(default=0)
    data_points = models.JSONField(default=list, blank=True)
    tracked_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ws_trend_detections"
        indexes = [
            models.Index(fields=["tenant_id", "topic", "tracked_at"]),
            models.Index(fields=["tenant_id", "stage"]),
            models.Index(fields=["source", "tracked_at"]),
        ]
        ordering = ["-tracked_at"]

    def __str__(self) -> str:
        return f"Trend({self.topic}, {self.stage}, score={self.trend_score})"
