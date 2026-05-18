"""OCRJob model — Tesseract OCR and table extraction from PDFs/images."""

from __future__ import annotations

import uuid

from django.db import models


class OCRJob(models.Model):
    """An OCR processing job for images or PDFs.

    Uses Tesseract for text extraction and Camelot for table
    extraction from structured PDFs. Supports preprocessing
    pipeline for image enhancement.

    Attributes:
        id: UUID primary key.
        tenant_id: Tenant scope identifier.
        file_url: URL or path to the source file.
        file_type: Type of file (image, pdf).
        languages: OCR language codes (comma-separated).
        status: Current processing status.
        extracted_text: Full extracted text content.
        avg_confidence: Average word confidence score (0-100).
        word_count: Total number of words extracted.
        words: JSON list of words with bounding boxes and confidence.
        lines: JSON list of text lines with bounding boxes.
        blocks: JSON list of text blocks with bounding boxes.
        tables: JSON list of extracted tables with data and accuracy.
        preprocessing_applied: JSON list of preprocessing steps applied.
        error_message: Error description on failure.
        processing_time_ms: Time taken to process in milliseconds.
        started_at: When processing began.
        completed_at: When processing finished.
        created_at: Record creation timestamp.
    """

    class FileType(models.TextChoices):
        IMAGE = "image", "Image"
        PDF = "pdf", "PDF"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    file_url = models.CharField(max_length=2048)
    file_type = models.CharField(
        max_length=10,
        choices=FileType.choices,
        default=FileType.IMAGE,
    )
    languages = models.CharField(max_length=100, default="eng")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    extracted_text = models.TextField(blank=True, default="")
    avg_confidence = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    word_count = models.PositiveIntegerField(default=0)
    words = models.JSONField(default=list, blank=True)
    lines = models.JSONField(default=list, blank=True)
    blocks = models.JSONField(default=list, blank=True)
    tables = models.JSONField(default=list, blank=True)
    preprocessing_applied = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True, default="")
    processing_time_ms = models.PositiveIntegerField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ws_ocr_jobs"
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"OCRJob({self.file_type}, {self.status})"
