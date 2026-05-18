"""Report builder and generation views.

Provides endpoints for report template CRUD, scheduling, on-demand
generation, and delivery configuration.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.analytics_v2.models.report import ReportSchedule, ReportTemplate
from apps.analytics_v2.serializers import (
    ReportGenerateIn,
    ReportGenerateOut,
    ReportScheduleCreateIn,
    ReportScheduleOut,
    ReportTemplateCreateIn,
    ReportTemplateOut,
    ReportTemplateUpdateIn,
)
from apps.analytics_v2.services.reports import deliver_report, generate_report
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


def _tenant_from_request(request) -> str:
    """Extract tenant_id from the authenticated request."""
    return getattr(request, "tenant_id", "default")


def _user_from_request(request) -> str:
    """Extract user_id from the authenticated request."""
    user = getattr(request, "auth", None)
    if user and hasattr(user, "sub"):
        return str(user.sub)
    return "anonymous"


# ---------------------------------------------------------------------------
# Report Template CRUD
# ---------------------------------------------------------------------------


@router.get("/report-templates", response=list[ReportTemplateOut], tags=["Reports"])
def list_report_templates(request, category: str = "", favorite: bool = False) -> list[ReportTemplate]:
    """List report templates for the current tenant.

    Args:
        category: Optional category filter.
        favorite: Filter to favorites only.
    """
    tenant_id = _tenant_from_request(request)
    qs = ReportTemplate.objects.filter(tenant_id=tenant_id)
    if category:
        qs = qs.filter(category=category)
    if favorite:
        qs = qs.filter(is_favorite=True)
    return list(qs)


@router.get("/report-templates/{template_id}", response=ReportTemplateOut, tags=["Reports"])
def get_report_template(request, template_id: UUID) -> ReportTemplate:
    """Get a single report template."""
    tenant_id = _tenant_from_request(request)
    return get_object_or_404(ReportTemplate, id=template_id, tenant_id=tenant_id)


@router.post("/report-templates", response=ReportTemplateOut, tags=["Reports"])
def create_report_template(request, payload: ReportTemplateCreateIn) -> ReportTemplate:
    """Create a new report template."""
    tenant_id = _tenant_from_request(request)
    user_id = _user_from_request(request)

    template = ReportTemplate.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        config=payload.config,
        format=payload.format,
        is_favorite=payload.is_favorite,
        created_by=user_id,
    )
    return template


@router.patch("/report-templates/{template_id}", response=ReportTemplateOut, tags=["Reports"])
def update_report_template(request, template_id: UUID, payload: ReportTemplateUpdateIn) -> ReportTemplate:
    """Update a report template."""
    tenant_id = _tenant_from_request(request)
    template = get_object_or_404(ReportTemplate, id=template_id, tenant_id=tenant_id)

    for attr in ["name", "description", "category", "config", "format", "is_favorite"]:
        val = getattr(payload, attr, None)
        if val is not None:
            setattr(template, attr, val)
    template.save()
    return template


@router.delete("/report-templates/{template_id}", tags=["Reports"])
def delete_report_template(request, template_id: UUID) -> dict[str, str]:
    """Delete a report template."""
    tenant_id = _tenant_from_request(request)
    template = get_object_or_404(ReportTemplate, id=template_id, tenant_id=tenant_id)
    template.delete()
    return {"status": "deleted", "id": str(template_id)}


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------


@router.post("/reports/generate", response=ReportGenerateOut, tags=["Reports"])
def generate_report_endpoint(request, payload: ReportGenerateIn) -> dict[str, Any]:
    """Generate a report on demand from a template.

    Executes the report pipeline: data collection, formatting, and delivery.
    """
    tenant_id = _tenant_from_request(request)
    template = get_object_or_404(ReportTemplate, id=payload.template_id, tenant_id=tenant_id)

    result = generate_report(
        template.config,
        payload.format,
        payload.date_range,
        payload.filters,
        tenant_id,
    )

    # Deliver if configured
    if payload.delivery:
        delivery_status = deliver_report(result, payload.delivery)
        result["delivery_status"] = delivery_status

    from uuid import uuid4

    return {
        "job_id": uuid4(),
        "status": result.get("status", "completed"),
        "format": result.get("format", payload.format),
        "download_url": None,
        "message": f"Report generated: {result.get('row_count', 0)} rows",
    }


@router.get("/reports/categories", tags=["Reports"])
def list_report_categories(request) -> dict[str, Any]:
    """List available report categories with metric counts."""
    tenant_id = _tenant_from_request(request)
    categories = (
        ReportTemplate.objects.filter(tenant_id=tenant_id)
        .values("category")
        .order_by("category")
        .distinct()
    )
    return {
        "categories": [
            {
                "name": cat["category"],
                "template_count": ReportTemplate.objects.filter(
                    tenant_id=tenant_id, category=cat["category"]
                ).count(),
            }
            for cat in categories
        ]
    }


# ---------------------------------------------------------------------------
# Report Scheduling
# ---------------------------------------------------------------------------


@router.get("/report-schedules", response=list[ReportScheduleOut], tags=["Reports"])
def list_report_schedules(request, active_only: bool = False) -> list[ReportSchedule]:
    """List report schedules for the current tenant."""
    tenant_id = _tenant_from_request(request)
    qs = ReportSchedule.objects.filter(tenant_id=tenant_id)
    if active_only:
        qs = qs.filter(is_active=True)
    return list(qs)


@router.post("/report-schedules", response=ReportScheduleOut, tags=["Reports"])
def create_report_schedule(request, payload: ReportScheduleCreateIn) -> ReportSchedule:
    """Create a report schedule."""
    tenant_id = _tenant_from_request(request)
    user_id = _user_from_request(request)
    template = get_object_or_404(ReportTemplate, id=payload.template_id, tenant_id=tenant_id)

    schedule = ReportSchedule.objects.create(
        tenant_id=tenant_id,
        template=template,
        name=payload.name,
        frequency=payload.frequency,
        cron_expression=payload.cron_expression,
        delivery=payload.delivery,
        timezone=payload.timezone,
        is_active=payload.is_active,
        created_by=user_id,
    )
    return schedule


@router.get("/report-schedules/{schedule_id}", response=ReportScheduleOut, tags=["Reports"])
def get_report_schedule(request, schedule_id: UUID) -> ReportSchedule:
    """Get a report schedule."""
    tenant_id = _tenant_from_request(request)
    return get_object_or_404(ReportSchedule, id=schedule_id, tenant_id=tenant_id)


@router.patch("/report-schedules/{schedule_id}/toggle", response=ReportScheduleOut, tags=["Reports"])
def toggle_report_schedule(request, schedule_id: UUID) -> ReportSchedule:
    """Toggle a report schedule active/inactive."""
    tenant_id = _tenant_from_request(request)
    schedule = get_object_or_404(ReportSchedule, id=schedule_id, tenant_id=tenant_id)
    schedule.is_active = not schedule.is_active
    schedule.save(update_fields=["is_active"])
    return schedule


@router.delete("/report-schedules/{schedule_id}", tags=["Reports"])
def delete_report_schedule(request, schedule_id: UUID) -> dict[str, str]:
    """Delete a report schedule."""
    tenant_id = _tenant_from_request(request)
    schedule = get_object_or_404(ReportSchedule, id=schedule_id, tenant_id=tenant_id)
    schedule.delete()
    return {"status": "deleted", "id": str(schedule_id)}
