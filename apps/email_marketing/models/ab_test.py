"""A/B testing model for email campaign experiments."""

from __future__ import annotations

from django.db import models


class EmailABTest(models.Model):
    """An A/B test for email campaigns (subject, content, send time).

    Supports multi-variant testing with automatic winner selection
    based on statistical significance.

    Attributes:
        id: Auto-incrementing primary key.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        name: Test name.
        test_type: What is being tested (subject, content, sender, time).
        status: Test lifecycle status.
        campaign_name: Name for the winning campaign.
        sample_size: Number of subscribers per variant.
        sample_pct: Percentage of list to test before winner.
        confidence_level: Statistical confidence (e.g. 0.95).
        winning_metric: Metric used to pick winner (opens, clicks, revenue).
        winner_variant_id: ID of the winning variant.
        winner_selected_at: When winner was determined.
        auto_deploy: Whether to auto-send winner to remaining list.
        total_sent: Total emails sent across all variants.
        total_conversions: Total conversions across all variants.
        variants: JSON variant definitions.
        results: JSON per-variant performance results.
        scheduled_at: When the test should start.
        started_at: When the test actually started.
        completed_at: When the test completed.
        created_at: Timestamp when created.
        updated_at: Timestamp when last updated.
    """

    class Status(models.TextChoices):
        """A/B test lifecycle statuses."""

        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        RUNNING = "running", "Running"
        WINNER_SELECTED = "winner_selected", "Winner Selected"
        DEPLOYED = "deployed", "Deployed"
        PAUSED = "paused", "Paused"
        CANCELLED = "cancelled", "Cancelled"

    class TestType(models.TextChoices):
        """What element is being tested."""

        SUBJECT = "subject", "Subject Line"
        CONTENT = "content", "Email Content"
        SENDER = "sender", "Sender Name"
        SEND_TIME = "send_time", "Send Time"
        MULTI = "multi", "Multi-variant"

    class WinningMetric(models.TextChoices):
        """Metrics for selecting a winner."""

        OPENS = "opens", "Open Rate"
        CLICKS = "clicks", "Click Rate"
        CTR = "ctr", "Click-Through Rate"
        REVENUE = "revenue", "Revenue"
        CONVERSIONS = "conversions", "Conversions"

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    name = models.CharField(
        max_length=255,
        help_text="Test name",
    )
    test_type = models.CharField(
        max_length=20,
        choices=TestType.choices,
        default=TestType.SUBJECT,
        db_index=True,
        help_text="What element is being tested",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text="Test lifecycle status",
    )
    campaign_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Name for the winning campaign",
    )
    sample_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of subscribers per variant",
    )
    sample_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20.00,
        help_text="Percentage of list to test before winner",
    )
    confidence_level = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        default=0.950,
        help_text="Statistical confidence level",
    )
    winning_metric = models.CharField(
        max_length=20,
        choices=WinningMetric.choices,
        default=WinningMetric.OPENS,
        help_text="Metric used to pick winner",
    )
    winner_variant_id = models.CharField(
        max_length=64,
        blank=True,
        help_text="ID of the winning variant",
    )
    winner_selected_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When winner was determined",
    )
    auto_deploy = models.BooleanField(
        default=True,
        help_text="Auto-send winner to remaining list",
    )
    total_sent = models.PositiveIntegerField(
        default=0,
        help_text="Total emails sent across all variants",
    )
    total_conversions = models.PositiveIntegerField(
        default=0,
        help_text="Total conversions across all variants",
    )
    variants = models.JSONField(
        default=list,
        help_text="Variant definitions (subject lines, content, etc.)",
    )
    results = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-variant performance results",
    )
    segment_id_ref = models.CharField(
        max_length=128,
        blank=True,
        help_text="Target audience segment reference",
    )
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the test should start",
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the test actually started",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the test completed",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when last updated",
    )

    class Meta:
        db_table = "voyager_email_ab_test"
        verbose_name = "Email A/B Test"
        verbose_name_plural = "Email A/B Tests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "test_type"]),
            models.Index(fields=["tenant_id", "scheduled_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.test_type})"

    @property
    def variant_count(self) -> int:
        """Return number of variants in the test."""
        return len(self.variants) if isinstance(self.variants, list) else 0

    @property
    def is_statistically_significant(self) -> bool:
        """Check if results meet the configured confidence level.

        Returns True if the p-value from chi-squared test
        indicates significance at the configured level.
        """
        if not self.results or not isinstance(self.results, dict):
            return False
        p_value = self.results.get("p_value")
        if p_value is None:
            return False
        alpha = 1 - float(self.confidence_level)
        return p_value < alpha

    @property
    def lift_pct(self) -> float:
        """Calculate percentage lift of winner vs runner-up."""
        if not self.results or not isinstance(self.results, dict):
            return 0.0
        variant_stats = self.results.get("variants", [])
        if len(variant_stats) < 2:
            return 0.0
        rates = []
        metric = self.winning_metric
        for v in variant_stats:
            count = v.get(metric, 0)
            sent = v.get("sent", 1)
            rates.append(count / sent if sent > 0 else 0)
        if len(rates) < 2:
            return 0.0
        rates.sort(reverse=True)
        if rates[1] == 0:
            return 0.0
        return round(((rates[0] - rates[1]) / rates[1]) * 100.0, 2)
