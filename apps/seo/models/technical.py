"""Technical crawl model.

Defines TechnicalCrawl for site-wide technical SEO auditing
with Core Web Vitals, error detection, and issue tracking.
"""

from __future__ import annotations

import uuid

from django.db import models


class TechnicalCrawl(models.Model):
    """A technical crawl result for a single page.

    Stores HTTP status, Core Web Vitals, structured data,
    hreflang tags, detected issues, and overall SEO score.
    """

    class Severity(models.TextChoices):
        """Issue severity levels."""

        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"
        INFO = "info", "Info"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    crawl_job_id = models.CharField(
        max_length=128, db_index=True, blank=True, help_text="Parent crawl job identifier"
    )
    url = models.URLField(max_length=2048, db_index=True, help_text="Crawled URL")
    status_code = models.PositiveIntegerField(
        null=True, blank=True, help_text="HTTP response status"
    )
    is_indexable = models.BooleanField(default=True, help_text="Whether page can be indexed")

    # Content
    word_count = models.PositiveIntegerField(default=0)
    title = models.TextField(blank=True)
    meta_description = models.TextField(blank=True)
    h1 = models.TextField(blank=True)
    h1_count = models.PositiveIntegerField(default=0)

    # Technical tags
    canonical = models.URLField(max_length=2048, blank=True)
    robots_meta = models.CharField(max_length=255, blank=True)
    hreflangs_json = models.JSONField(
        default=list, blank=True, help_text="Hreflang tag declarations"
    )

    # Core Web Vitals
    lcp_ms = models.PositiveIntegerField(
        null=True, blank=True, help_text="Largest Contentful Paint in ms"
    )
    fid_ms = models.PositiveIntegerField(null=True, blank=True, help_text="First Input Delay in ms")
    cls_score = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Cumulative Layout Shift",
    )
    ttfb_ms = models.PositiveIntegerField(
        null=True, blank=True, help_text="Time to First Byte in ms"
    )
    page_size_kb = models.PositiveIntegerField(
        null=True, blank=True, help_text="Page size in kilobytes"
    )
    load_time_ms = models.PositiveIntegerField(
        null=True, blank=True, help_text="Total page load time in ms"
    )

    # Structured data
    structured_data_json = models.JSONField(
        default=list, blank=True, help_text="JSON-LD structured data"
    )
    schema_errors_json = models.JSONField(
        default=list, blank=True, help_text="Schema validation errors"
    )

    # Issues
    issues_json = models.JSONField(default=list, blank=True, help_text="Technical issues detected")

    # Scoring
    seo_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, help_text="Page SEO score 0-100"
    )

    # Mobile
    is_mobile_friendly = models.BooleanField(null=True, blank=True)

    # Link extraction
    internal_links_json = models.JSONField(default=list, blank=True)
    external_links_json = models.JSONField(default=list, blank=True)
    broken_links_json = models.JSONField(default=list, blank=True)

    metadata_json = models.JSONField(default=dict, blank=True)
    crawled_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "voyager_technical_crawl"
        verbose_name = "Technical Crawl"
        verbose_name_plural = "Technical Crawls"
        ordering = ["-crawled_at"]
        indexes = [
            models.Index(fields=["tenant_id", "url"]),
            models.Index(fields=["tenant_id", "crawl_job_id"]),
            models.Index(fields=["tenant_id", "-seo_score"]),
            models.Index(fields=["tenant_id", "status_code"]),
            models.Index(fields=["tenant_id", "is_indexable"]),
            models.Index(fields=["tenant_id", "-crawled_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.url} (HTTP {self.status_code})"

    def cwv_status(self) -> dict[str, str]:
        """Return Core Web Vitals status assessment.

        Returns:
            Dict with 'lcp', 'fid', 'cls' keys each mapping to
            'good', 'needs_improvement', or 'poor'.
        """
        result: dict[str, str] = {}
        if self.lcp_ms is not None:
            if self.lcp_ms <= 2500:
                result["lcp"] = "good"
            elif self.lcp_ms <= 4000:
                result["lcp"] = "needs_improvement"
            else:
                result["lcp"] = "poor"
        if self.fid_ms is not None:
            if self.fid_ms <= 100:
                result["fid"] = "good"
            elif self.fid_ms <= 300:
                result["fid"] = "needs_improvement"
            else:
                result["fid"] = "poor"
        if self.cls_score is not None:
            cls_val = float(self.cls_score)
            if cls_val <= 0.1:
                result["cls"] = "good"
            elif cls_val <= 0.25:
                result["cls"] = "needs_improvement"
            else:
                result["cls"] = "poor"
        return result
