"""GDPR consent and DSR API endpoint handlers."""

from __future__ import annotations

from django.http import HttpRequest
from ninja import Query
from ninja.errors import HttpError

from apps.governance_v2.models import DSRRequest
from apps.governance_v2.serializers import (
    ConsentRecordRequest,
    ConsentRecordSchema,
    ConsentStatusResponse,
    DSRListResponse,
    DSRRequestSchema,
    DSRSubmitRequest,
    DSRUpdateRequest,
)
from apps.governance_v2.services import GDPRService


def record_consent(
    request: HttpRequest,
    payload: ConsentRecordRequest,
) -> ConsentRecordSchema:
    """Record or update a user's consent for a specific purpose.

    Args:
        request: HTTP request.
        payload: Consent record data.

    Returns:
        The recorded consent entry.
    """
    ip = request.META.get("REMOTE_ADDR") or payload.ip_address
    result = GDPRService.record_consent(
        user_id=payload.user_id,
        tenant_id=payload.tenant_id,
        consent_type=payload.consent_type,
        granted=payload.granted,
        source=payload.source,
        ip_address=ip,
        user_agent=payload.user_agent or request.META.get("HTTP_USER_AGENT", ""),
    )

    return ConsentRecordSchema(
        id=result["id"],
        user_id=result["user_id"],
        tenant_id=result["tenant_id"],
        consent_type=result["consent_type"],
        granted=result["granted"],
        source=result["source"],
        ip_address=result["ip_address"],
        user_agent=result["user_agent"],
        created_at=result["created_at"],
    )


def list_dsrf(
    request: HttpRequest,
    user_id: str,
    tenant_id: str,
) -> ConsentStatusResponse:
    """List consent status for a user.

    Args:
        request: HTTP request.
        user_id: User identifier.
        tenant_id: Tenant identifier.

    Returns:
        Current consent status for all consent types.
    """
    consents = GDPRService.get_consent_status(user_id, tenant_id)

    return ConsentStatusResponse(
        user_id=user_id,
        tenant_id=tenant_id,
        consents=[
            ConsentRecordSchema(
                id=c["id"],
                user_id=c["user_id"],
                tenant_id=c["tenant_id"],
                consent_type=c["consent_type"],
                granted=c["granted"],
                source=c["source"],
                ip_address=c["ip_address"],
                user_agent=c["user_agent"],
                created_at=c["created_at"],
            )
            for c in consents
        ],
    )


def list_dsr_requests(
    request: HttpRequest,
    tenant_id: str = Query(..., description="Tenant identifier"),
    status: str | None = Query(None, description="Filter by status"),
    request_type: str | None = Query(None, description="Filter by request type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> DSRListResponse:
    """List data subject requests for a tenant.

    Args:
        request: HTTP request.
        tenant_id: Tenant identifier.
        status: Optional status filter.
        request_type: Optional request type filter.
        page: Page number (1-indexed).
        page_size: Items per page.

    Returns:
        Paginated list of DSR requests.
    """
    qs = DSRRequest.objects.filter(tenant_id=tenant_id)
    if status:
        qs = qs.filter(status=status)
    if request_type:
        qs = qs.filter(request_type=request_type)

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = qs.order_by("-created_at")[start:end]

    return DSRListResponse(
        items=[
            DSRRequestSchema(
                id=d.id,
                tenant_id=d.tenant_id,
                user_id=d.user_id,
                email=d.email,
                request_type=d.request_type,
                status=d.status,
                deadline=d.deadline,
                completed_at=d.completed_at,
                verified_at=d.verified_at,
                processed_by=d.processed_by,
                notes=d.notes,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


def submit_dsr(
    request: HttpRequest,
    payload: DSRSubmitRequest,
) -> DSRRequestSchema:
    """Submit a new data subject request.

    Args:
        request: HTTP request.
        payload: DSR submission data.

    Returns:
        The created DSR request.
    """
    result = GDPRService.submit_dsr(
        tenant_id=payload.tenant_id,
        email=payload.email,
        request_type=payload.request_type,
        user_id=payload.user_id,
        notes=payload.notes,
    )

    return DSRRequestSchema(
        id=result["id"],
        tenant_id=result["tenant_id"],
        user_id=result["user_id"],
        email=result["email"],
        request_type=result["request_type"],
        status=result["status"],
        deadline=result["deadline"],
        completed_at=result["completed_at"],
        verified_at=result["verified_at"],
        processed_by=result["processed_by"],
        notes=result["notes"],
        created_at=result["created_at"],
        updated_at=result["updated_at"],
    )


def update_dsr(
    request: HttpRequest,
    dsr_id: int,
    payload: DSRUpdateRequest,
) -> DSRRequestSchema:
    """Update a data subject request status.

    Args:
        request: HTTP request.
        dsr_id: ID of the DSR to update.
        payload: DSR update data.

    Returns:
        The updated DSR.

    Raises:
        HttpError(404): If the DSR is not found.
    """
    try:
        dsr = DSRRequest.objects.get(id=dsr_id)
    except DSRRequest.DoesNotExist:
        raise HttpError(404, f"DSR {dsr_id} not found")

    fields = ["status", "notes", "processed_by"]
    update_fields = []
    for field in fields:
        value = getattr(payload, field, None)
        if value is not None:
            setattr(dsr, field, value)
            update_fields.append(field)

    if update_fields:
        update_fields.append("updated_at")
        dsr.save(update_fields=update_fields)

    return DSRRequestSchema(
        id=dsr.id,
        tenant_id=dsr.tenant_id,
        user_id=dsr.user_id,
        email=dsr.email,
        request_type=dsr.request_type,
        status=dsr.status,
        deadline=dsr.deadline,
        completed_at=dsr.completed_at,
        verified_at=dsr.verified_at,
        processed_by=dsr.processed_by,
        notes=dsr.notes,
        created_at=dsr.created_at,
        updated_at=dsr.updated_at,
    )
