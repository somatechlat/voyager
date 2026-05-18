"""CampaignABTest model for statistical A/B testing."""

from __future__ import annotations

from django.db import models

from apps.campaigns.models.campaign import Campaign


class CampaignABTest(models.Model):
    """An A/B test associated with a campaign.

    Supports frequentist (chi-squared) and Bayesian statistical methods
    with configurable sample sizes, significance levels, and winner criteria.

    Attributes:
        id: Auto-incrementing primary key.
        campaign: Parent campaign.
        name: Test name.
        test_type: Type of element being tested.
        method: Statistical method (frequentist or bayesian).
        significance_level: Alpha level (e.g. 0.05).
        power: Statistical power (e.g. 0.80).
        sample_size_per_variant: Required sample size per variant.
        actual_sample_size: Actual sample size reached.
        baseline_rate: Baseline conversion rate.
        minimum_detectable_effect: Relative lift to detect.
        daily_traffic: Expected daily visitors.
        estimated_duration_days: Calculated test duration.
        status: Test lifecycle status.
        winner_criteria: Metric for selecting winner.
        winner_variant_id: ID of winning variant.
        variants: JSON array of test variants.
        results: JSON test results.
        start_date: When the test started.
        end_date: When the test ended.
        created_at: Timestamp when created.
        updated_at: Timestamp when last updated.
    """

    class TestType(models.TextChoices):
        """Types of A/B test elements."""

        SUBJECT_LINE = "subject_line", "Subject Line"
        CREATIVE = "creative", "Creative"
        LANDING_PAGE = "landing_page", "Landing Page"
        AUDIENCE = "audience", "Audience"
        BID_STRATEGY = "bid_strategy", "Bid Strategy"
        AD_COPY = "ad_copy", "Ad Copy"
        CTA = "cta", "Call to Action"
        PLACEMENT = "placement", "Placement"

    class Method(models.TextChoices):
        """Statistical analysis methods."""

        FREQUENTIST = "frequentist", "Frequentist"
        BAYESIAN = "bayesian", "Bayesian"

    class Status(models.TextChoices):
        """Test lifecycle statuses."""

        DRAFT = "draft", "Draft"
        RUNNING = "running", "Running"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class WinnerCriteria(models.TextChoices):
        """Metrics for selecting a winner."""

        CONVERSION_RATE = "conversion_rate", "Conversion Rate"
        CLICK_RATE = "click_rate", "Click Rate"
        REVENUE = "revenue", "Revenue"
        ROAS = "roas", "ROAS"
        CPA = "cpa", "CPA"
        ENGAGEMENT = "engagement", "Engagement"

    id = models.BigAutoField(primary_key=True, editable=False)
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="ab_tests",
        help_text="Parent campaign",
    )
    name = models.CharField(max_length=255, help_text="Test name")
    test_type = models.CharField(
        max_length=30,
        choices=TestType.choices,
        db_index=True,
        help_text="Type of element being tested",
    )
    method = models.CharField(
        max_length=15,
        choices=Method.choices,
        default=Method.FREQUENTIST,
        help_text="Statistical method",
    )
    significance_level = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0.05,
        help_text="Alpha level (e.g. 0.05)",
    )
    power = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0.80,
        help_text="Statistical power (e.g. 0.80)",
    )
    sample_size_per_variant = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Required sample size per variant",
    )
    actual_sample_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Actual sample size reached",
    )
    baseline_rate = models.DecimalField(
        max_digits=7,
        decimal_places=5,
        null=True,
        blank=True,
        help_text="Baseline conversion rate (e.g. 0.05)",
    )
    minimum_detectable_effect = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Relative lift to detect (e.g. 0.20)",
    )
    daily_traffic = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Expected daily visitors",
    )
    estimated_duration_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Calculated test duration in days",
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text="Test lifecycle status",
    )
    winner_criteria = models.CharField(
        max_length=20,
        choices=WinnerCriteria.choices,
        default=WinnerCriteria.CONVERSION_RATE,
        help_text="Metric for selecting winner",
    )
    winner_variant_id = models.CharField(
        max_length=128,
        blank=True,
        help_text="ID of winning variant",
    )
    variants = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of test variants with id, name, traffic_split",
    )
    results = models.JSONField(
        default=dict,
        blank=True,
        help_text="Test results (z-statistic, p-value, credible intervals)",
    )
    start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the test started",
    )
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the test ended",
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
        db_table = "voyager_campaign_ab_test"
        verbose_name = "Campaign A/B Test"
        verbose_name_plural = "Campaign A/B Tests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["campaign", "status"]),
            models.Index(fields=["campaign", "test_type"]),
            models.Index(fields=["method", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.test_type} — {self.method})"
