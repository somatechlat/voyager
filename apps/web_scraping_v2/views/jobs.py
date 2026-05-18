"""Scrape job API endpoints."""

from __future__ import annotations

import logging
from uuid import UUID

from django.http import HttpRequest
from ninja import Query
from ninja.errors import HttpError

from ..models import ScrapeJob
from ..serializers import (
    ScrapeJobCreateSchema,
    ScrapeJobListResponse,
    ScrapeJobSchema,
)
from ..services.scraper import PlaywrightScraper

logger = logging.getLogger(__name__)


def create_scrape_job(
    request: HttpRequest,
    payload: ScrapeJobCreateSchema,
) -> ScrapeJobSchema:
    """Create and execute a new scrape job.

    Args:
        request: HTTP request.
        payload: Scrape job creation data.

    Returns:
        The created scrape job with results.

    Raises:
        HttpError: 400 if URL is invalid.
    """
    if not payload.url.startswith(("http://", "https://")):
        raise HttpError(400, "Invalid URL: must start with http:// or https://")

    job = ScrapeJob.objects.create(
        tenant_id=payload.tenant_id,
        url=payload.url,
        selector=payload.selector,
        status=ScrapeJob.Status.RUNNING,
    )

    try:
        scraper = PlaywrightScraper()
        result = scraper.scrape(payload.url, selector=payload.selector or None)

        job.status = ScrapeJob.Status.COMPLETED
        job.content_text = result.get("content_text", "")
        job.content_html = result.get("content_html", "")
        job.metadata = result.get("metadata", {})
        job.proxy_used = result.get("proxy_used", "")
    except Exception as exc:
        logger.error("Scrape job failed for %s: %s", payload.url, exc)
        job.status = ScrapeJob.Status.FAILED
        job.error_message = str(exc)

    job.save()

    return ScrapeJobSchema(
        id=job.id,
        tenant_id=job.tenant_id,
        url=job.url,
        selector=job.selector,
        proxy_used=job.proxy_used,
        status=job.status,
        content_text=job.content_text,
        content_html=job.content_html,
        metadata=job.metadata,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def list_scrape_jobs(
    request: HttpRequest,
    tenant_id: str = Query("", description="Filter by tenant"),
    status: str = Query("", description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ScrapeJobListResponse:
    """List scrape jobs with optional filtering.

    Args:
        request: HTTP request.
        tenant_id: Optional tenant filter.
        status: Optional status filter.
        page: Page number (1-indexed).
        page_size: Items per page.

    Returns:
        Paginated scrape job list.
    """
    qs = ScrapeJob.objects.all()

    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if status:
        qs = qs.filter(status=status)

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = qs.order_by("-created_at")[start:end]

    return ScrapeJobListResponse(
        items=[
            ScrapeJobSchema(
                id=j.id,
                tenant_id=j.tenant_id,
                url=j.url,
                selector=j.selector,
                proxy_used=j.proxy_used,
                status=j.status,
                content_text=j.content_text,
                content_html=j.content_html,
                metadata=j.metadata,
                error_message=j.error_message,
                started_at=j.started_at,
                completed_at=j.completed_at,
                created_at=j.created_at,
                updated_at=j.updated_at,
            )
            for j in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_scrape_job(
    request: HttpRequest,
    job_id: UUID,
) -> ScrapeJobSchema:
    """Get a single scrape job by ID.

    Args:
        request: HTTP request.
        job_id: UUID of the job.

    Returns:
        The scrape job.

    Raises:
        HttpError: 404 if not found.
    """
    try:
        job = ScrapeJob.objects.get(id=job_id)
    except ScrapeJob.DoesNotExist:
        raise HttpError(404, f"Scrape job {job_id} not found")

    return ScrapeJobSchema(
        id=job.id,
        tenant_id=job.tenant_id,
        url=job.url,
        selector=job.selector,
        proxy_used=job.proxy_used,
        status=job.status,
        content_text=job.content_text,
        content_html=job.content_html,
        metadata=job.metadata,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
