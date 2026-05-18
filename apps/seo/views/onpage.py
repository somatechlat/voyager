"""On-page audit views.

API endpoints for page-level SEO auditing, issue detection,
and recommendation retrieval.
"""

from __future__ import annotations

import logging
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.seo.models.onpage import OnPageAudit
from apps.seo.serializers import (
    OnPageAuditRequest,
    OnPageAuditResponse,
    OnPageIssue,
    OnPageRecommendation,
    OnPageTechnicalDetails,
)
from apps.seo.services.onpage import audit_page

logger = logging.getLogger(__name__)

router = Router(auth=VoyagerKeycloakBearer())


def _audit_to_schema(audit: OnPageAudit) -> OnPageAuditResponse:
    """Convert OnPageAudit model to response schema."""
    issues = [
        OnPageIssue(
            type=i.get("type", ""),
            severity=i.get("severity", "medium"),
            details={k: v for k, v in i.items() if k not in ("type", "severity")},
        )
        for i in (audit.issues_json or [])
    ]
    recommendations = [
        OnPageRecommendation(
            issueType=r.get("issue_type", ""),
            description=r.get("description", ""),
            priority=r.get("priority", "medium"),
            details=r.get("details"),
        )
        for r in (audit.recommendations_json or [])
    ]
    tech_details = OnPageTechnicalDetails(
        wordCount=audit.word_count,
        readability=float(audit.readability_score) if audit.readability_score else 0.0,
        internalLinks=audit.internal_links,
        externalLinks=audit.external_links,
        images=audit.images_total,
        imagesWithAlt=audit.images_with_alt,
        schemas=audit.schema_count,
    )
    return OnPageAuditResponse(
        id=str(audit.id),
        url=audit.url,
        score=float(audit.score) if audit.score else 0.0,
        grade=audit.grade,
        issues=issues,
        recommendations=recommendations,
        technicalDetails=tech_details,
        title=audit.title or "",
        metaDescription=audit.meta_description or "",
        h1Count=audit.h1_count,
        auditedAt=audit.audited_at,
    )


@router.post("/audits/onpage", response=OnPageAuditResponse, tags=["SEO On-Page"])
def create_onpage_audit(request, data: OnPageAuditRequest) -> OnPageAuditResponse:
    """Run a comprehensive on-page SEO audit.

    Analyzes title, meta, headings, images, links, content length,
    keyword density, readability, and schema markup.
    """
    tenant_id = getattr(request, "tenant_id", "default")
    audit = audit_page(
        tenant_id=tenant_id,
        url=data.url,
        title=data.title,
        meta_description=data.metaDescription,
        h1_tags=data.h1Tags or [],
        headings=data.headings or [],
        body_text=data.bodyText,
        images=data.images or [],
        internal_links=data.internalLinks,
        external_links=data.externalLinks,
        canonical=data.canonical,
        og_tags=data.ogTags or [],
        schemas=data.schemas or [],
        target_keywords=data.targetKeywords or [],
    )
    return _audit_to_schema(audit)


@router.get("/audits/onpage", response=list[OnPageAuditResponse], tags=["SEO On-Page"])
def list_onpage_audits(
    request,
    limit: int = 50,
    url_filter: str = "",
) -> list[OnPageAuditResponse]:
    """List on-page audits for the tenant.

    Query parameters:
        limit: Maximum results.
        url_filter: Filter by URL substring.
    """
    tenant_id = getattr(request, "tenant_id", "default")
    qs = OnPageAudit.objects.filter(tenant_id=tenant_id)
    if url_filter:
        qs = qs.filter(url__icontains=url_filter)
    return [_audit_to_schema(a) for a in qs[:limit]]


@router.get("/audits/onpage/{audit_id}", response=OnPageAuditResponse, tags=["SEO On-Page"])
def get_onpage_audit(request, audit_id: str) -> OnPageAuditResponse:
    """Get a single on-page audit by ID."""
    tenant_id = getattr(request, "tenant_id", "default")
    audit = get_object_or_404(OnPageAudit, id=audit_id, tenant_id=tenant_id)
    return _audit_to_schema(audit)
