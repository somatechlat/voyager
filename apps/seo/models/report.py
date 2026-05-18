"""SEO report model.

Defines SEOReport for automated white-label report generation
with multiple sections and customizable branding.
"""

from __future__ import annotations

import uuid

from django.db import models


class SEOReport(models.Model):
    """An automated SEO report with white-label support.

    Stores report configuration, section data, branding,
    and scheduling information for client-ready SEO reports.
    """

    class ReportType(models.TextChoices):
        """Types of SEO reports."""

        EXECUTIVE = "executive", "Executive Summary"
        KEYWORD = "keyword", "Keyword Rankings"
        BACKLINK = "backlink", "Backlink Profile"
        TECHNICAL = "technical", "Technical Health"
        CONTENT = "content", "Content Score"
        COMPREHENSIVE = "comprehensive", "Comprehensive"

    class ReportFrequency(models.TextChoices):
        """Report generation frequency."""

        ONE_TIME = "one_time", "One Time"
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"

    class Status(models.TextChoices):
        """Report lifecycle status."""

        PENDING = "pending", "Pending"
        GENERATING = "generating", "Generating"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    name = models.CharField(max_length=255, help_text="Report name")
    report_type = models.CharField(
        max_length=20, choices=ReportType.choices, default=ReportType.COMPREHENSIVE
    )
    frequency = models.CharField(
        max_length=16,
        choices=ReportFrequency.choices,
        default=ReportFrequency.MONTHLY,
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )

    # Report sections
    sections_json = models.JSONField(
        default=list,
        blank=True,
        help_text="Enabled report sections",
    )

    # Date range
    date_from = models.DateField(help_text="Report period start")
    date_to = models.DateField(help_text="Report period end")

    # White-label branding
    brand_logo_url = models.URLField(max_length=2048, blank=True)
    brand_primary_color = models.CharField(max_length=7, blank=True)
    brand_name = models.CharField(max_length=255, blank=True)
    custom_header = models.TextField(blank=True)
    custom_footer = models.TextField(blank=True)

    # Report data
    executive_summary_json = models.JSONField(default=dict, blank=True)
    keyword_rankings_json = models.JSONField(default=dict, blank=True)
    backlink_profile_json = models.JSONField(default=dict, blank=True)
    technical_health_json = models.JSONField(default=dict, blank=True)
    content_score_json = models.JSONField(default=dict, blank=True)

    # File output
    report_file = models.FileField(
        upload_to="seo_reports/%Y/%m/",
        blank=True,
        help_text="Generated report file (PDF/HTML)",
    )
    file_format = models.CharField(
        max_length=10, default="pdf", help_text="pdf or html"
    )

    # Comparison
    compare_with_previous = models.BooleanField(
        default=True, help_text="Compare with previous period"
    )
    previous_period_json = models.JSONField(default=dict, blank=True)

    # Scheduling
    is_scheduled = models.BooleanField(default=False, db_index=True)
    next_run_at = models.DateTimeField(null=True, blank=True, db_index=True)

    # Recipients
    recipients_json = models.JSONField(
        default=list, blank=True, help_text="Email addresses for report delivery"
    )

    # Error tracking
    error_message = models.TextField(blank=True)

    metadata_json = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "voyager_seo_report"
        verbose_name = "SEO Report"
        verbose_name_plural = "SEO Reports"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "report_type"]),
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "is_scheduled"]),
            models.Index(fields=["tenant_id", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.report_type}) [{self.status}]"
