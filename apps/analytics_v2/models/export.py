"""Export job model for large-scale data export with streaming support.

Handles CSV, JSON, and Excel exports with progress tracking for
 datasets exceeding 100,000 rows.
"""

from __future__ import annotations

import uuid

from django.db import models

from apps.rbac.models import TenantScopedMixin

EXPORT_FORMAT_CHOICES = [
    ("csv", "CSV"),
    ("json", "JSON"),
    ("excel", "Excel (.xlsx)"),
    ("ndjson", "Newline-Delimited JSON"),
]

EXPORT_STATUS_CHOICES = [
    ("queued", "Queued"),
    ("running", "Running"),
    ("completed", "Completed"),
    ("failed", "Failed"),
    ("cancelled", "Cancelled"),
    ("expired", "Expired"),
]


class ExportJob(TenantScopedMixin, models.Model):
    """A data export job with streaming support for large datasets.

    Attributes:
        id: UUID primary key.
        tenant_id: Tenant scope identifier.
        name: Human-readable export name.
        description: Optional export description.
        query: The query/filters used to select data.
        format: Output file format.
        columns: JSON list of column names to export.
        row_count: Number of rows exported.
        file_size_bytes: Size of the generated file.
        file_path: Path to the generated file.
        download_url: Temporary download URL.
        download_expires_at: When the download URL expires.
        status: Current export status.
        progress_percent: Export progress (0-100).
        error_message: Error details if failed.
        started_at: When export processing began.
        completed_at: When export processing finished.
        created_by: User ID who requested the export.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    query = models.JSONField(
        default=dict,
        help_text="Query config: source, filters, date_range, aggregations",
    )
    format = models.CharField(
        max_length=16,
        choices=EXPORT_FORMAT_CHOICES,
        default="csv",
    )
    columns = models.JSONField(
        default=list,
        help_text="Column names to include in the export",
    )
    row_count = models.PositiveBigIntegerField(default=0)
    file_size_bytes = models.PositiveBigIntegerField(default=0)
    file_path = models.CharField(max_length=512, blank=True)
    download_url = models.URLField(blank=True)
    download_expires_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=EXPORT_STATUS_CHOICES,
        default="queued",
    )
    progress_percent = models.PositiveSmallIntegerField(default=0)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = "analytics_export_job"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status", "-created_at"]),
            models.Index(fields=["tenant_id", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Export {self.name} ({self.format})"
