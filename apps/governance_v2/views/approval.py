"""Approval workflow API endpoint handlers."""

from __future__ import annotations

from django.http import HttpRequest
from ninja import Query
from ninja.errors import HttpError

from apps.governance_v2.models import ApprovalRequest
from apps.governance_v2.serializers import (
    ApprovalActionSchema,
    ApprovalRequestCreateSchema,
    ApprovalRequestListResponse,
    ApprovalRequestSchema,
)
from apps.governance_v2.services import ApprovalService


def list_approvals(
    request: HttpRequest,
    tenant_id: str = Query(..., description="Tenant identifier"),
    status: str | None = Query(None, description="Filter by status"),
    gate_id: int | None = Query(None, description="Filter by approval gate"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ApprovalRequestListResponse:
    """List approval requests for a tenant.

    Args:
        request: HTTP request.
        tenant_id: Tenant identifier.
        status: Optional status filter.
        gate_id: Optional gate filter.
        page: Page number (1-indexed).
        page_size: Items per page.

    Returns:
        Paginated list of approval requests.
    """
    qs = ApprovalRequest.objects.filter(tenant_id=tenant_id)
    if status:
        qs = qs.filter(status=status)
    if gate_id:
        qs = qs.filter(gate_id=gate_id)

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = qs.select_related("gate").order_by("-created_at")[start:end]

    return ApprovalRequestListResponse(
        items=[
            ApprovalRequestSchema(
                id=a.id,
                gate_id=a.gate.id,
                tenant_id=a.tenant_id,
                requester_id=a.requester_id,
                requester_email=a.requester_email,
                status=a.status,
                approved_by=a.approved_by,
                rejected_by=a.rejected_by,
                justification=a.justification,
                rejection_reason=a.rejection_reason,
                escalated_at=a.escalated_at,
                escalated_to=a.escalated_to,
                completed_at=a.completed_at,
                due_at=a.due_at,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


def create_approval(
    request: HttpRequest,
    payload: ApprovalRequestCreateSchema,
) -> ApprovalRequestSchema:
    """Create a new approval request.

    Args:
        request: HTTP request.
        payload: Approval request creation data.

    Returns:
        The created approval request.

    Raises:
        HttpError(400): If the gate is invalid or disabled.
    """
    result = ApprovalService.create_approval_request(
        gate_id=payload.gate_id,
        tenant_id=payload.tenant_id,
        requester_id=payload.requester_id,
        requester_email=payload.requester_email,
        justification=payload.justification,
    )

    if "error" in result:
        raise HttpError(400, result["error"])

    return ApprovalRequestSchema(
        id=result["id"],
        gate_id=result["gate_id"],
        tenant_id=result["tenant_id"],
        requester_id=result["requester_id"],
        requester_email=result["requester_email"],
        status=result["status"],
        approved_by=result["approved_by"],
        rejected_by="",
        justification=result["justification"],
        rejection_reason="",
        escalated_at=None,
        escalated_to="",
        completed_at=result["completed_at"],
        due_at=result["due_at"],
        created_at=result["created_at"],
        updated_at=result["updated_at"],
    )


def approve_request(
    request: HttpRequest,
    request_id: int,
    payload: ApprovalActionSchema,
) -> ApprovalRequestSchema:
    """Process an approval action (approve, reject, or override).

    Args:
        request: HTTP request.
        request_id: ID of the approval request.
        payload: Approval action data.

    Returns:
        The updated approval request.

    Raises:
        HttpError(400): If the action is invalid.
        HttpError(404): If the request is not found.
    """
    try:
        ApprovalRequest.objects.get(id=request_id)
    except ApprovalRequest.DoesNotExist:
        raise HttpError(404, f"Approval request {request_id} not found")

    result = ApprovalService.process_approval(
        request_id=request_id,
        approver_id=payload.approver_id,
        action=payload.action,
        reason=payload.reason,
    )

    if "error" in result:
        raise HttpError(400, result["error"])

    return ApprovalRequestSchema(
        id=result["id"],
        gate_id=result["gate_id"],
        tenant_id=result["tenant_id"],
        requester_id=result["requester_id"],
        requester_email="",
        status=result["status"],
        approved_by=result["approved_by"],
        rejected_by=result["rejected_by"],
        justification=result["justification"],
        rejection_reason=result["rejection_reason"],
        escalated_at=result["escalated_at"],
        escalated_to=result["escalated_to"],
        completed_at=result["completed_at"],
        due_at=result["due_at"],
        updated_at=result["updated_at"],
    )
