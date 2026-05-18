"""SEO report views.

API endpoints for automated SEO report generation,
white-label configuration, and report retrieval.
"""

from __future__ import annotations

import logging
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.seo.models.report import SEOReport
from apps.seo.serializers import (
    ReportCreateRequest,
    ReportDetailResponse,
    ReportResponse,
    ReportScheduleRequest,
)
from apps.seo.services.reporting import generate_report

logger = logging.getLogger(__name__)

router = Router(auth=VoyagerKeycloakBearer())


def _report_to_schema(report: SEOReport) -> ReportResponse:
    """Convert SEOReport model to response schema."""
    return ReportResponse(
        id=str(report.id),
        name=report.name,
        reportType=report.report_type,
        frequency=report.frequency,
        status=report.status,
        sections=report.sections_json or [],
        dateFrom=report.date_from,
        dateTo=report.date_to,
        brandName=report.brand_name or "",
        generatedAt=report.generated_at,
        isScheduled=report.is_scheduled,
        nextRunAt=report.next_run_at,
        createdAt=report.created_at,
    )


def _report_to_detail(report: SEOReport) -> ReportDetailResponse:
    """Convert SEOReport model to detailed response schema."""
    return ReportDetailResponse(
        id=str(report.id),
        name=report.name,
        reportType=report.report_type,
        status=report.status,
        sections=report.sections_json or [],
        dateFrom=report.date_from,
        dateTo=report.date_to,
        executiveSummary=report.executive_summary_json or {},
        keywordRankings=report.keyword_rankings_json or {},
        backlinkProfile=report.backlink_profile_json or {},
        technicalHealth=report.technical_health_json or {},
        contentScore=report.content_score_json or {},
        previousPeriod=report.previous_period_json or {},
        generatedAt=report.generated_at,
    )


@router.post("/reports", response=ReportResponse, tags=["SEO Reports"])
def create_report(request, data: ReportCreateRequest) -> ReportResponse:
    """Generate an SEO report.

    Creates a comprehensive report with the requested sections
    and optional period-over-period comparison.
    """
    tenant_id = getattr(request, "tenant_id", "default")
    report = generate_report(
        tenant_id=tenant_id,
        name=data.name,
        report_type=data.reportType,
        date_from=data.dateFrom,
        date_to=data.dateTo,
        sections=data.sections,
        compare=data.compareWithPrevious,
        brand_name=data.brandName,
        brand_primary_color=data.brandPrimaryColor,
        brand_logo_url=data.brandLogoUrl,
        custom_header=data.customHeader,
        custom_footer=data.customFooter,
        recipients=data.recipients,
    )
    return _report_to_schema(report)


@router.get("/reports", response=list[ReportResponse], tags=["SEO Reports"])
def list_reports(
    request,
    limit: int = 50,
    report_type: str = "",
) -> list[ReportResponse]:
    """List SEO reports for the tenant.

    Query parameters:
        limit: Maximum results.
        report_type: Filter by report type.
    """
    tenant_id = getattr(request, "tenant_id", "default")
    qs = SEOReport.objects.filter(tenant_id=tenant_id)
    if report_type:
        qs = qs.filter(report_type=report_type)
    return [_report_to_schema(r) for r in qs[:limit]]


@router.get("/reports/{report_id}", response=ReportDetailResponse, tags=["SEO Reports"])
def get_report(request, report_id: str) -> ReportDetailResponse:
    """Get a single SEO report by ID with all sections."""
    tenant_id = getattr(request, "tenant_id", "default")
    report = get_object_or_404(SEOReport, id=report_id, tenant_id=tenant_id)
    return _report_to_detail(report)


@router.patch("/reports/{report_id}/schedule", response=ReportResponse, tags=["SEO Reports"])
def schedule_report(request, report_id: str, data: ReportScheduleRequest) -> ReportResponse:
    """Configure report scheduling.

    Enable or disable recurring report generation with
    specified frequency and recipients.
    """
    tenant_id = getattr(request, "tenant_id", "default")
    report = get_object_or_404(SEOReport, id=report_id, tenant_id=tenant_id)
    report.is_scheduled = data.isScheduled
    report.frequency = data.frequency
    if data.recipients:
        report.recipients_json = data.recipients
    report.save(update_fields=["is_scheduled", "frequency", "recipients_json"])
    return _report_to_schema(report)


@router.delete("/reports/{report_id}", tags=["SEO Reports"])
def delete_report(request, report_id: str) -> dict[str, Any]:
    """Delete an SEO report."""
    tenant_id = getattr(request, "tenant_id", "default")
    report = get_object_or_404(SEOReport, id=report_id, tenant_id=tenant_id)
    report.delete()
    return {"status": "ok", "report_id": report_id, "deleted": True}


@router.get("/reports/{report_id}/summary", tags=["SEO Reports"])
def get_report_summary(request, report_id: str) -> dict[str, Any]:
    """Get a quick summary of a report without full details."""
    tenant_id = getattr(request, "tenant_id", "default")
    report = get_object_or_404(SEOReport, id=report_id, tenant_id=tenant_id)
    return {
        "id": str(report.id),
        "name": report.name,
        "type": report.report_type,
        "status": report.status,
        "sections": report.sections_json or [],
        "executive_summary": report.executive_summary_json or {},
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
    }
