"""ScrapeJob model — URL scraping with Playwright and proxy rotation."""

from __future__ import annotations

import uuid

from django.db import models


class ScrapeJob(models.Model):
    """A web scraping job targeting a specific URL with configurable selectors.

    Uses Playwright for JavaScript-rendered pages and rotates through
    a pool of residential proxies to avoid bot detection.

    Attributes:
        id: UUID primary key.
        tenant_id: Tenant scope for multi-tenancy isolation.
        url: Target URL to scrape.
        selector: Optional CSS selector for targeted extraction.
        proxy_used: The proxy that was used for this scrape.
        status: Current job status.
        content_text: Extracted text content.
        content_html: Extracted raw HTML content.
        metadata: JSON with headers, cookies, timing info.
        error_message: Error description on failure.
        started_at: When the job began execution.
        completed_at: When the job finished.
        created_at: Record creation timestamp.
        updated_at: Last modification timestamp.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    url = models.URLField(max_length=2048)
    selector = models.CharField(max_length=512, blank=True, default="")
    proxy_used = models.CharField(max_length=512, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    content_text = models.TextField(blank=True, default="")
    content_html = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ws_scrape_jobs"
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"ScrapeJob({self.url}, {self.status})"
