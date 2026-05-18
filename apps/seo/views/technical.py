"""Technical crawl views.

API endpoints for technical SEO crawling, Core Web Vitals assessment,
and crawl job management.
"""

from __future__ import annotations

import logging
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.seo.models.technical import TechnicalCrawl
from apps.seo.serializers import (
    CrawlSummaryResponse,
    TechnicalCrawlRequest,
    TechnicalCrawlResponse,
    TechnicalIssue,
)
from apps.seo.services.technical import crawl_page, get_crawl_summary

logger = logging.getLogger(__name__)

router = Router(auth=VoyagerKeycloakBearer())


def _crawl_to_schema(crawl: TechnicalCrawl) -> TechnicalCrawlResponse:
    """Convert TechnicalCrawl model to response schema."""
    cwv = crawl.cwv_status()
    issues = [
        TechnicalIssue(
            type=i.get("type", ""),
            severity=i.get("severity", "low"),
            details={k: v for k, v in i.items() if k not in ("type", "severity")},
        )
        for i in (crawl.issues_json or [])
    ]
    return TechnicalCrawlResponse(
        id=str(crawl.id),
        url=crawl.url,
        statusCode=crawl.status_code,
        isIndexable=crawl.is_indexable,
        seoScore=float(crawl.seo_score) if crawl.seo_score else None,
        issues=issues,
        coreWebVitals=cwv,
        lcpMs=crawl.lcp_ms,
        fidMs=crawl.fid_ms,
        clsScore=float(crawl.cls_score) if crawl.cls_score else None,
        ttfbMs=crawl.ttfb_ms,
        loadTimeMs=crawl.load_time_ms,
        pageSizeKb=crawl.page_size_kb,
        isMobileFriendly=crawl.is_mobile_friendly,
        crawledAt=crawl.crawled_at,
    )


@router.post("/crawls", response=TechnicalCrawlResponse, tags=["SEO Technical"])
def create_crawl(request, data: TechnicalCrawlRequest) -> TechnicalCrawlResponse:
    """Submit a page crawl result for technical SEO analysis.

    Analyzes Core Web Vitals, structured data, hreflang, and
    generates a technical issue report.
    """
    tenant_id = getattr(request, "tenant_id", "default")
    crawl = crawl_page(
        tenant_id=tenant_id,
        crawl_job_id=data.crawlJobId,
        url=data.url,
        status_code=data.statusCode,
        title=data.title,
        meta_description=data.metaDescription,
        h1=data.h1,
        h1_count=data.h1Count,
        canonical=data.canonical,
        hreflangs=data.hreflangs or [],
        structured_data=data.structuredData or [],
        lcp_ms=data.lcpMs,
        fid_ms=data.fidMs,
        cls_score=data.clsScore,
        ttfb_ms=data.ttfbMs,
        page_size_kb=data.pageSizeKb,
        load_time_ms=data.loadTimeMs,
        robots_meta=data.robotsMeta,
        is_mobile_friendly=data.isMobileFriendly,
        is_indexable=data.isIndexable,
        word_count=data.wordCount,
        internal_links=data.internalLinks or [],
        external_links=data.externalLinks or [],
        broken_links=data.brokenLinks or [],
    )
    return _crawl_to_schema(crawl)


@router.get("/crawls", response=list[TechnicalCrawlResponse], tags=["SEO Technical"])
def list_crawls(
    request,
    limit: int = 50,
    crawl_job_id: str = "",
) -> list[TechnicalCrawlResponse]:
    """List technical crawls for the tenant.

    Query parameters:
        limit: Maximum results.
        crawl_job_id: Filter by crawl job ID.
    """
    tenant_id = getattr(request, "tenant_id", "default")
    qs = TechnicalCrawl.objects.filter(tenant_id=tenant_id)
    if crawl_job_id:
        qs = qs.filter(crawl_job_id=crawl_job_id)
    return [_crawl_to_schema(c) for c in qs[:limit]]


@router.get("/crawls/{crawl_id}", response=TechnicalCrawlResponse, tags=["SEO Technical"])
def get_crawl(request, crawl_id: str) -> TechnicalCrawlResponse:
    """Get a single crawl result by ID."""
    tenant_id = getattr(request, "tenant_id", "default")
    crawl = get_object_or_404(TechnicalCrawl, id=crawl_id, tenant_id=tenant_id)
    return _crawl_to_schema(crawl)


@router.get("/crawls/summary/{crawl_job_id}", response=CrawlSummaryResponse, tags=["SEO Technical"])
def crawl_summary(request, crawl_job_id: str) -> dict[str, Any]:
    """Get summary statistics for a crawl job."""
    tenant_id = getattr(request, "tenant_id", "default")
    return get_crawl_summary(tenant_id, crawl_job_id)
