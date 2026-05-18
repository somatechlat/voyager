"""Celery tasks for the Governance v2 module.

Periodic and on-demand tasks for compliance checks, DSR deadline
alerts, approval escalation, and brand safety scanning.

Tasks are routed to the ``governance`` queue via
``voyager_project.celery.app.conf.task_routes``.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

from apps.governance_v2.services import ApprovalService, GDPRService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_compliance_check(
    self,
    content: str,
    tenant_id: str,
    industry: str,
    regulations: list[str] | None = None,
) -> dict[str, Any]:
    """Run compliance check against content asynchronously.

    Args:
        content: Text content to validate.
        tenant_id: Tenant identifier for rule scoping.
        industry: Industry sector.
        regulations: Optional regulation codes to check.

    Returns:
        Dict with compliance check results.
    """
    from apps.governance_v2.services import ComplianceService

    logger.info(
        "Running compliance check for tenant %s, industry %s",
        tenant_id,
        industry,
    )

    result = ComplianceService.validate_compliance(
        content=content,
        tenant_id=tenant_id,
        industry=industry,
        regulations=regulations,
    )

    return {
        "status": "completed",
        "task": self.name,
        "tenant_id": tenant_id,
        "industry": industry,
        "overall_compliant": result["overall_compliant"],
        "violation_count": len(result["violations"]),
        "checked_at": result["checked_at"].isoformat(),
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def seed_compliance_rules(self, tenant_id: str) -> dict[str, Any]:
    """Seed built-in compliance rules for a tenant.

    Args:
        tenant_id: Target tenant identifier.

    Returns:
        Dict with number of rules created.
    """
    from apps.governance_v2.services import ComplianceService

    logger.info("Seeding compliance rules for tenant %s", tenant_id)

    count = ComplianceService.seed_builtin_rules(tenant_id)

    return {
        "status": "completed",
        "task": self.name,
        "tenant_id": tenant_id,
        "rules_created": count,
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_dsr_deadlines(self, tenant_id: str | None = None) -> dict[str, Any]:
    """Check for DSRs approaching or past their deadline.

    Scans all pending DSRs and logs warnings for those within
    48 hours of deadline and errors for expired ones.

    Args:
        tenant_id: Optional tenant filter. If not provided,
                   checks all tenants.

    Returns:
        Dict with counts of near-deadline and expired DSRs.
    """
    from apps.governance_v2.models import DSRRequest

    logger.info("Checking DSR deadlines for tenant %s", tenant_id or "ALL")

    if tenant_id:
        near_deadline = GDPRService.get_pending_dsr_deadlines(tenant_id)
        expired = GDPRService.get_expired_dsrs(tenant_id)
    else:
        # Collect from all tenants
        tenant_ids = list(DSRRequest.objects.values_list("tenant_id", flat=True).distinct())
        near_deadline = []
        expired = []
        for tid in tenant_ids:
            near_deadline.extend(GDPRService.get_pending_dsr_deadlines(tid))
            expired.extend(GDPRService.get_expired_dsrs(tid))

    for dsr in near_deadline:
        logger.warning(
            "DSR %s deadline approaching: %s hours remaining",
            dsr["id"],
            dsr["hours_remaining"],
        )

    for dsr in expired:
        logger.error(
            "DSR %s EXPIRED: %s hours overdue",
            dsr["id"],
            dsr["hours_overdue"],
        )

    return {
        "status": "completed",
        "task": self.name,
        "tenant_id": tenant_id,
        "near_deadline_count": len(near_deadline),
        "expired_count": len(expired),
        "near_deadline_ids": [d["id"] for d in near_deadline],
        "expired_ids": [d["id"] for d in expired],
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def escalate_pending_approvals(
    self,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Escalate approval requests past their escalation threshold.

    Scans pending approval requests and escalates those that have
    exceeded their configured escalation timeout.

    Args:
        tenant_id: Optional tenant filter. If not provided,
                   checks all tenants.

    Returns:
        Dict with the list of escalated requests.
    """
    from apps.governance_v2.models import ApprovalRequest

    logger.info(
        "Escalating pending approvals for tenant %s",
        tenant_id or "ALL",
    )

    if tenant_id:
        escalated = ApprovalService.check_escalations(tenant_id)
    else:
        tenant_ids = list(ApprovalRequest.objects.values_list("tenant_id", flat=True).distinct())
        escalated = []
        for tid in tenant_ids:
            escalated.extend(ApprovalService.check_escalations(tid))

    for req in escalated:
        logger.info(
            "Escalated approval request %s for gate '%s' to %s",
            req["id"],
            req["gate_name"],
            req["escalated_to"],
        )

    return {
        "status": "completed",
        "task": self.name,
        "tenant_id": tenant_id,
        "escalated_count": len(escalated),
        "escalated_ids": [r["id"] for r in escalated],
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def scan_content_brand_safety(
    self,
    content: str,
    tenant_id: str,
    industry: str = "general",
) -> dict[str, Any]:
    """Scan content for brand safety violations asynchronously.

    Args:
        content: Text content to scan.
        tenant_id: Tenant identifier.
        industry: Industry context.

    Returns:
        Dict with scan results summary.
    """
    from apps.governance_v2.services import BrandSafetyService

    logger.info(
        "Scanning content for tenant %s, industry %s",
        tenant_id,
        industry,
    )

    result = BrandSafetyService.scan_content(
        content=content,
        tenant_id=tenant_id,
        industry=industry,
    )

    return {
        "status": "completed",
        "task": self.name,
        "tenant_id": tenant_id,
        "passed": result["passed"],
        "action": result["action"],
        "violation_count": len(result["violations"]),
        "scan_timestamp": result["scan_timestamp"].isoformat(),
    }
