"""Deliverability monitoring dashboard views."""

from __future__ import annotations

import logging
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.email_marketing.models.deliverability import DeliverabilityMonitor
from apps.email_marketing.serializers import (
    BounceClassifySchema,
    DeliverabilityCreateSchema,
    DeliverabilityDetailSchema,
    DeliverabilityListSchema,
    DeliverabilityUpdateSchema,
    ReputationCalcSchema,
)
from apps.email_marketing.services.deliverability import (
    calculate_reputation_score,
    check_authentication,
    classify_bounce,
)

logger = logging.getLogger(__name__)

router = Router()


@router.get("/", response=list[DeliverabilityListSchema])
def list_monitors(
    request,
    tenant_id: str = "",
    domain: str = "",
    limit: int = 50,
    offset: int = 0,
) -> list[DeliverabilityMonitor]:
    """List deliverability monitors.

    Args:
        request: HTTP request.
        tenant_id: Filter by tenant.
        domain: Filter by domain.
        limit: Page size.
        offset: Pagination offset.

    Returns:
        List of deliverability monitors.
    """
    qs = DeliverabilityMonitor.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if domain:
        qs = qs.filter(domain__icontains=domain)
    return list(qs.order_by("-checked_at")[offset : offset + limit])


@router.post("/", response=DeliverabilityDetailSchema)
def create_monitor(
    request,
    payload: DeliverabilityCreateSchema,
) -> DeliverabilityMonitor:
    """Create a deliverability monitor for a domain.

    Args:
        request: HTTP request.
        payload: Monitor creation data.

    Returns:
        Created monitor.
    """
    data = payload.dict()
    monitor = DeliverabilityMonitor.objects.create(**data)
    logger.info("Deliverability monitor %s created for %s", monitor.id, monitor.domain)
    return monitor


@router.get("/{monitor_id}", response=DeliverabilityDetailSchema)
def get_monitor(
    request,
    monitor_id: int,
) -> DeliverabilityMonitor:
    """Get a deliverability monitor.

    Args:
        request: HTTP request.
        monitor_id: Monitor primary key.

    Returns:
        Deliverability monitor.
    """
    return get_object_or_404(DeliverabilityMonitor, id=monitor_id)


@router.put("/{monitor_id}", response=DeliverabilityDetailSchema)
def update_monitor(
    request,
    monitor_id: int,
    payload: DeliverabilityUpdateSchema,
) -> DeliverabilityMonitor:
    """Update a deliverability monitor.

    Args:
        request: HTTP request.
        monitor_id: Monitor primary key.
        payload: Update data.

    Returns:
        Updated monitor.
    """
    monitor = get_object_or_404(DeliverabilityMonitor, id=monitor_id)
    data = payload.dict(exclude_unset=True)
    for attr, val in data.items():
        setattr(monitor, attr, val)
    monitor.save()
    return monitor


@router.delete("/{monitor_id}")
def delete_monitor(
    request,
    monitor_id: int,
) -> dict[str, bool]:
    """Delete a deliverability monitor.

    Args:
        request: HTTP request.
        monitor_id: Monitor primary key.

    Returns:
        Success dict.
    """
    monitor = get_object_or_404(DeliverabilityMonitor, id=monitor_id)
    monitor.delete()
    return {"success": True}


@router.post("/classify-bounce")
def bounce_classify(
    request,
    payload: BounceClassifySchema,
) -> dict[str, Any]:
    """Classify a bounce by SMTP code.

    Args:
        request: HTTP request.
        payload: Bounce data.

    Returns:
        Classification result.
    """
    result = classify_bounce(payload.bounce_code, payload.retry_count)
    return result


@router.post("/{monitor_id}/calculate-reputation")
def calculate_reputation(
    request,
    monitor_id: int,
    payload: ReputationCalcSchema,
) -> dict[str, Any]:
    """Calculate reputation score for a monitored domain.

    Args:
        request: HTTP request.
        monitor_id: Monitor primary key.
        payload: Metrics data.

    Returns:
        Reputation score and recommendations.
    """
    monitor = get_object_or_404(DeliverabilityMonitor, id=monitor_id)
    metrics = payload.dict()
    result = calculate_reputation_score(metrics)
    monitor.reputation_score = result["score"]
    monitor.reputation_grade = result["grade"]
    monitor.recommendations = result["recommendations"]
    monitor.save(update_fields=["reputation_score", "reputation_grade", "recommendations"])
    return result


@router.post("/{monitor_id}/check-auth")
def check_auth(
    request,
    monitor_id: int,
) -> dict[str, Any]:
    """Check authentication records for a monitored domain.

    Args:
        request: HTTP request.
        monitor_id: Monitor primary key.

    Returns:
        Authentication check results.
    """
    monitor = get_object_or_404(DeliverabilityMonitor, id=monitor_id)
    result = check_authentication(monitor.domain)
    spf = result.get("spf", {})
    dkim = result.get("dkim", {})
    dmarc = result.get("dmarc", {})
    bimi = result.get("bimi", {})
    monitor.spf_configured = spf.get("configured", False)
    monitor.spf_valid = spf.get("valid", False)
    monitor.spf_includes = spf.get("includes", [])
    monitor.dkim_configured = dkim.get("configured", False)
    monitor.dkim_valid = dkim.get("valid", False)
    monitor.dmarc_configured = dmarc.get("configured", False)
    monitor.dmarc_policy = dmarc.get("policy", "unknown")
    monitor.dmarc_rua = dmarc.get("rua", "")
    monitor.dmarc_ruf = dmarc.get("ruf", "")
    monitor.bimi_configured = bimi.get("configured", False)
    monitor.bimi_logo_url = bimi.get("logo_url", "")
    monitor.save()
    return result


@router.get("/{monitor_id}/health")
def monitor_health(
    request,
    monitor_id: int,
) -> dict[str, Any]:
    """Get deliverability health summary.

    Args:
        request: HTTP request.
        monitor_id: Monitor primary key.

    Returns:
        Health summary dict.
    """
    monitor = get_object_or_404(DeliverabilityMonitor, id=monitor_id)
    return {
        "domain": monitor.domain,
        "reputation_score": float(monitor.reputation_score),
        "reputation_grade": monitor.reputation_grade,
        "is_healthy": monitor.is_healthy,
        "authentication_score": monitor.authentication_score,
        "spf": monitor.spf_configured and monitor.spf_valid,
        "dkim": monitor.dkim_configured and monitor.dkim_valid,
        "dmarc": monitor.dmarc_configured,
        "bimi": monitor.bimi_configured,
        "bounce_rate": float(monitor.bounce_rate),
        "spam_complaint_rate": float(monitor.spam_complaint_rate),
        "recommendations": monitor.recommendations,
    }
