"""Compliance rule API endpoint handlers."""

from __future__ import annotations

from django.http import HttpRequest
from ninja import Query
from ninja.errors import HttpError

from apps.governance_v2.models import ComplianceRule
from apps.governance_v2.serializers import (
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    ComplianceRuleCreateSchema,
    ComplianceRuleListResponse,
    ComplianceRuleSchema,
    ComplianceRuleUpdateSchema,
)
from apps.governance_v2.services import ComplianceService


def list_compliance_rules(
    request: HttpRequest,
    tenant_id: str = Query(..., description="Tenant identifier"),
    industry: str | None = Query(None, description="Filter by industry"),
    regulation: str | None = Query(None, description="Filter by regulation"),
    enabled: bool | None = Query(None, description="Filter by enabled status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ComplianceRuleListResponse:
    """List compliance rules for a tenant.

    Args:
        request: HTTP request.
        tenant_id: Tenant identifier.
        industry: Optional industry filter.
        regulation: Optional regulation filter.
        enabled: Optional enabled status filter.
        page: Page number (1-indexed).
        page_size: Items per page.

    Returns:
        Paginated list of compliance rules.
    """
    qs = ComplianceRule.objects.filter(tenant_id=tenant_id)
    if industry:
        qs = qs.filter(industry=industry)
    if regulation:
        qs = qs.filter(regulation__icontains=regulation)
    if enabled is not None:
        qs = qs.filter(enabled=enabled)

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = qs.order_by("-created_at")[start:end]

    return ComplianceRuleListResponse(
        items=[
            ComplianceRuleSchema(
                id=r.id,
                tenant_id=r.tenant_id,
                industry=r.industry,
                regulation=r.regulation,
                name=r.name,
                description=r.description,
                check_type=r.check_type,
                check_config=r.check_config,
                severity=r.severity,
                legal_reference=r.legal_reference,
                remediation=r.remediation,
                enabled=r.enabled,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


def create_compliance_rule(
    request: HttpRequest,
    payload: ComplianceRuleCreateSchema,
) -> ComplianceRuleSchema:
    """Create a new compliance rule.

    Args:
        request: HTTP request.
        payload: Compliance rule creation data.

    Returns:
        The created compliance rule.
    """
    rule = ComplianceRule.objects.create(
        tenant_id=payload.tenant_id,
        industry=payload.industry,
        regulation=payload.regulation,
        name=payload.name,
        description=payload.description,
        check_type=payload.check_type,
        check_config=payload.check_config,
        severity=payload.severity,
        legal_reference=payload.legal_reference,
        remediation=payload.remediation,
        enabled=payload.enabled,
    )

    return ComplianceRuleSchema(
        id=rule.id,
        tenant_id=rule.tenant_id,
        industry=rule.industry,
        regulation=rule.regulation,
        name=rule.name,
        description=rule.description,
        check_type=rule.check_type,
        check_config=rule.check_config,
        severity=rule.severity,
        legal_reference=rule.legal_reference,
        remediation=rule.remediation,
        enabled=rule.enabled,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


def update_compliance_rule(
    request: HttpRequest,
    rule_id: int,
    payload: ComplianceRuleUpdateSchema,
) -> ComplianceRuleSchema:
    """Update an existing compliance rule.

    Args:
        request: HTTP request.
        rule_id: ID of the rule to update.
        payload: Compliance rule update data.

    Returns:
        The updated compliance rule.

    Raises:
        HttpError(404): If the rule is not found.
    """
    try:
        rule = ComplianceRule.objects.get(id=rule_id)
    except ComplianceRule.DoesNotExist:
        raise HttpError(404, f"Compliance rule {rule_id} not found")

    fields = [
        "industry",
        "regulation",
        "name",
        "description",
        "check_type",
        "check_config",
        "severity",
        "legal_reference",
        "remediation",
        "enabled",
    ]
    update_fields = []
    for field in fields:
        value = getattr(payload, field, None)
        if value is not None:
            setattr(rule, field, value)
            update_fields.append(field)

    if update_fields:
        update_fields.append("updated_at")
        rule.save(update_fields=update_fields)

    return ComplianceRuleSchema(
        id=rule.id,
        tenant_id=rule.tenant_id,
        industry=rule.industry,
        regulation=rule.regulation,
        name=rule.name,
        description=rule.description,
        check_type=rule.check_type,
        check_config=rule.check_config,
        severity=rule.severity,
        legal_reference=rule.legal_reference,
        remediation=rule.remediation,
        enabled=rule.enabled,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


def check_compliance(
    request: HttpRequest,
    payload: ComplianceCheckRequest,
) -> ComplianceCheckResponse:
    """Run a compliance check against content.

    Args:
        request: HTTP request.
        payload: Compliance check request data.

    Returns:
        Compliance check results.
    """
    result = ComplianceService.validate_compliance(
        content=payload.content,
        tenant_id=payload.tenant_id,
        industry=payload.industry,
        regulations=payload.regulations or None,
    )

    return ComplianceCheckResponse(
        content_id=result["content_id"],
        industry=result["industry"],
        regulations=result["regulations"],
        overall_compliant=result["overall_compliant"],
        violations=result["violations"],
        checked_at=result["checked_at"],
    )
