"""Client profitability API endpoints."""

from __future__ import annotations

from ninja import Router

from apps.clients.serializers import (
    PaginatedProfitabilitySchema,
    ProfitabilityCreateSchema,
    ProfitabilitySchema,
    ProfitabilityUpdateSchema,
)
from apps.clients.services import ProfitabilityService
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


def _get_tenant(request) -> str:
    """Extract tenant_id from the authenticated user."""
    return getattr(request.auth, "tenant_id", "default")


@router.get(
    "/clients/{client_id}/profitability",
    response=PaginatedProfitabilitySchema,
    tags=["Profitability"],
)
def list_client_profitability(request, client_id: int):
    """List profitability records for a client."""
    tenant_id = _get_tenant(request)
    qs = ProfitabilityService.list_records(tenant_id, client_id)
    items = list(qs[:100])
    return PaginatedProfitabilitySchema(
        count=qs.count(),
        items=[
            ProfitabilitySchema(
                id=r.id,
                tenant_id=r.tenant_id,
                client_id=r.client_id,
                period_start=r.period_start,
                period_end=r.period_end,
                revenue=r.revenue,
                costs=r.costs,
                margin_percent=r.margin_percent,
                gross_profit=r.gross_profit,
                breakdown=r.breakdown,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in items
        ],
    )


@router.post(
    "/clients/{client_id}/profitability",
    response=ProfitabilitySchema,
    tags=["Profitability"],
)
def create_profitability(request, client_id: int, payload: ProfitabilityCreateSchema):
    """Create a profitability record for a client."""
    tenant_id = _get_tenant(request)
    data = payload.dict()
    record = ProfitabilityService.create(tenant_id, client_id, data)
    return ProfitabilitySchema(
        id=record.id,
        tenant_id=record.tenant_id,
        client_id=record.client_id,
        period_start=record.period_start,
        period_end=record.period_end,
        revenue=record.revenue,
        costs=record.costs,
        margin_percent=record.margin_percent,
        gross_profit=record.gross_profit,
        breakdown=record.breakdown,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get(
    "/profitability/{record_id}",
    response=ProfitabilitySchema,
    tags=["Profitability"],
)
def get_profitability(request, record_id: int):
    """Retrieve a profitability record."""
    tenant_id = _get_tenant(request)
    record = ProfitabilityService.get_by_id(tenant_id, record_id)
    return ProfitabilitySchema(
        id=record.id,
        tenant_id=record.tenant_id,
        client_id=record.client_id,
        period_start=record.period_start,
        period_end=record.period_end,
        revenue=record.revenue,
        costs=record.costs,
        margin_percent=record.margin_percent,
        gross_profit=record.gross_profit,
        breakdown=record.breakdown,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.put(
    "/profitability/{record_id}",
    response=ProfitabilitySchema,
    tags=["Profitability"],
)
def update_profitability(request, record_id: int, payload: ProfitabilityUpdateSchema):
    """Update a profitability record."""
    tenant_id = _get_tenant(request)
    record = ProfitabilityService.get_by_id(tenant_id, record_id)
    data = {k: v for k, v in payload.dict().items() if v is not None}
    updated = ProfitabilityService.update(record, data)
    return ProfitabilitySchema(
        id=updated.id,
        tenant_id=updated.tenant_id,
        client_id=updated.client_id,
        period_start=updated.period_start,
        period_end=updated.period_end,
        revenue=updated.revenue,
        costs=updated.costs,
        margin_percent=updated.margin_percent,
        gross_profit=updated.gross_profit,
        breakdown=updated.breakdown,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.delete("/profitability/{record_id}", tags=["Profitability"])
def delete_profitability(request, record_id: int):
    """Delete a profitability record."""
    tenant_id = _get_tenant(request)
    record = ProfitabilityService.get_by_id(tenant_id, record_id)
    ProfitabilityService.delete(record)
    return {"success": True, "message": f"Profitability record {record_id} deleted"}


@router.get("/clients/{client_id}/profitability/summary", tags=["Profitability"])
def get_profitability_summary(request, client_id: int):
    """Get a profitability summary for a client."""
    tenant_id = _get_tenant(request)
    return ProfitabilityService.get_client_summary(tenant_id, client_id)
