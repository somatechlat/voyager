"""OCR processing API endpoints."""

from __future__ import annotations

import base64
import logging
from uuid import UUID

from django.http import HttpRequest
from ninja import Query, Schema
from ninja.errors import HttpError

from ..models import OCRJob
from ..serializers import (
    OCRJobCreateSchema,
    OCRJobListResponse,
    OCRJobSchema,
    OCRProcessResponse,
)
from ..services.ocr import OCRProcessor

logger = logging.getLogger(__name__)


def create_ocr_job(
    request: HttpRequest,
    payload: OCRJobCreateSchema,
) -> OCRJobSchema:
    """Create an OCR processing job.

    Args:
        request: HTTP request.
        payload: OCR job creation data.

    Returns:
        The created OCR job.

    Raises:
        HttpError: 400 if file_url is missing or file_type is invalid.
    """
    if not payload.file_url or not payload.file_url.strip():
        raise HttpError(400, "file_url is required")

    if payload.file_type not in (OCRJob.FileType.IMAGE, OCRJob.FileType.PDF):
        raise HttpError(400, f"Invalid file_type: {payload.file_type}")

    job = OCRJob.objects.create(
        tenant_id=payload.tenant_id,
        file_url=payload.file_url,
        file_type=payload.file_type,
        languages=payload.languages,
        status=OCRJob.Status.PENDING,
    )

    return OCRJobSchema(
        id=job.id,
        tenant_id=job.tenant_id,
        file_url=job.file_url,
        file_type=job.file_type,
        languages=job.languages,
        status=job.status,
        extracted_text=job.extracted_text,
        avg_confidence=job.avg_confidence,
        word_count=job.word_count,
        words=job.words,
        lines=job.lines,
        blocks=job.blocks,
        tables=job.tables,
        preprocessing_applied=job.preprocessing_applied,
        error_message=job.error_message,
        processing_time_ms=job.processing_time_ms,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
    )


def get_ocr_job(
    request: HttpRequest,
    job_id: UUID,
) -> OCRJobSchema:
    """Get an OCR job by ID.

    Args:
        request: HTTP request.
        job_id: UUID of the job.

    Returns:
        The OCR job.

    Raises:
        HttpError: 404 if not found.
    """
    try:
        job = OCRJob.objects.get(id=job_id)
    except OCRJob.DoesNotExist:
        raise HttpError(404, f"OCR job {job_id} not found")

    return OCRJobSchema(
        id=job.id,
        tenant_id=job.tenant_id,
        file_url=job.file_url,
        file_type=job.file_type,
        languages=job.languages,
        status=job.status,
        extracted_text=job.extracted_text,
        avg_confidence=job.avg_confidence,
        word_count=job.word_count,
        words=job.words,
        lines=job.lines,
        blocks=job.blocks,
        tables=job.tables,
        preprocessing_applied=job.preprocessing_applied,
        error_message=job.error_message,
        processing_time_ms=job.processing_time_ms,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
    )


def list_ocr_jobs(
    request: HttpRequest,
    tenant_id: str = Query("", description="Filter by tenant"),
    status: str = Query("", description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> OCRJobListResponse:
    """List OCR jobs with optional filtering.

    Args:
        request: HTTP request.
        tenant_id: Optional tenant filter.
        status: Optional status filter.
        page: Page number (1-indexed).
        page_size: Items per page.

    Returns:
        Paginated OCR job list.
    """
    qs = OCRJob.objects.all()

    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if status:
        qs = qs.filter(status=status)

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = qs.order_by("-created_at")[start:end]

    return OCRJobListResponse(
        items=[
            OCRJobSchema(
                id=j.id,
                tenant_id=j.tenant_id,
                file_url=j.file_url,
                file_type=j.file_type,
                languages=j.languages,
                status=j.status,
                extracted_text=j.extracted_text,
                avg_confidence=j.avg_confidence,
                word_count=j.word_count,
                words=j.words,
                lines=j.lines,
                blocks=j.blocks,
                tables=j.tables,
                preprocessing_applied=j.preprocessing_applied,
                error_message=j.error_message,
                processing_time_ms=j.processing_time_ms,
                started_at=j.started_at,
                completed_at=j.completed_at,
                created_at=j.created_at,
            )
            for j in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


class OCRProcessInlineSchema(Schema):
    """Inline OCR request body."""

    image_base64: str
    languages: str = "eng"


def process_image_ocr(
    request: HttpRequest,
    payload: OCRProcessInlineSchema,
) -> OCRProcessResponse:
    """Process a base64-encoded image inline (no DB persistence).

    Args:
        request: HTTP request.
        payload: OCR inline processing data.

    Returns:
        OCR processing result.

    Raises:
        HttpError: 400 if image data is missing or invalid.
    """
    image_b64 = payload.image_base64
    if not image_b64:
        raise HttpError(400, "image_base64 is required")

    languages_str = payload.languages
    languages = languages_str.split(",") if languages_str else ["eng"]

    try:
        image_data = base64.b64decode(image_b64)
    except Exception:
        raise HttpError(400, "Invalid base64 image data")

    processor = OCRProcessor()
    result = processor.process_image(image_data, languages=languages)

    if "error" in result:
        raise HttpError(422, result["error"])

    return OCRProcessResponse(
        text=result.get("text", ""),
        confidence=result.get("confidence", 0),
        word_count=result.get("word_count", 0),
        words=result.get("words", []),
        lines=result.get("lines", []),
        blocks=result.get("blocks", []),
        tables=result.get("tables", []),
        preprocessing=result.get("preprocessing", []),
    )
