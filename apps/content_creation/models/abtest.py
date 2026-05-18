"""ABTest model — A/B testing for content variations.

Tracks test configuration, variant performance, statistical results,
and winner selection for content optimization.
"""

from __future__ import annotations

from django.db import models

from .base import TenantModel, UUIDModel


class ABTest(UUIDModel, TenantModel):
    """An A/B test comparing content variants.

    Attributes:
        name: Human-readable test name.
        content_generation_id: Base content being tested.
        variants: JSON list of variant content objects.
        status: Lifecycle state of the test.
        start_date: When the test started.
        end_date: When the test ended / will end.
        sample_size: Target number of impressions per variant.
        winner_criteria: Metric used to determine winner (ctr, conversion, engagement).
        results: JSON statistical results and winner info.
        created_at: Timestamp when the test was created.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        ARCHIVED = "archived", "Archived"

    class WinnerCriteria(models.TextChoices):
        CTR = "ctr", "Click-Through Rate"
        CONVERSION = "conversion", "Conversion Rate"
        ENGAGEMENT = "engagement", "Engagement Rate"

    name = models.CharField(
        max_length=255,
        help_text="Human-readable test name",
    )
    content_generation_id = models.UUIDField(
        db_index=True,
        help_text="Base content generation being tested",
    )
    variants = models.JSONField(
        default=list,
        blank=True,
        help_text="List of variant content objects",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text="Current test lifecycle state",
    )
    start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the test started",
    )
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the test ended / will end",
    )
    sample_size = models.IntegerField(
        null=True,
        blank=True,
        help_text="Target impressions per variant",
    )
    winner_criteria = models.CharField(
        max_length=20,
        choices=WinnerCriteria.choices,
        default=WinnerCriteria.CTR,
        help_text="Metric used to select the winner",
    )
    results = models.JSONField(
        default=dict,
        blank=True,
        help_text="Statistical results and winner information",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when the test was created",
    )

    class Meta:
        db_table = "voyager_ab_test"
        verbose_name = "A/B Test"
        verbose_name_plural = "A/B Tests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "content_generation_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"
