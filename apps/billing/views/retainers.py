"""Retainer views.

API endpoints for retainer agreement management, consumption tracking,
and rollover calculation.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.billing.models.retainer import Retainer
from apps.billing.serializers import (
    RetainerConsumptionSchema,
    RetainerCreateSchema,
    RetainerListSchema,
    RetainerRolloverSchema,
    RetainerSchema,
    RetainerUpdateSchema,
)
from apps.billing.services.retainers import (
    calculate_monthly_usage,
    calculate_rollover,
    check_consumption_alerts,
    renew_retainer,
    should_auto_renew,
)
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/retainers", response=list[RetainerListSchema], tags=["Billing"])
def list_retainers(
    request,
    client_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List retainers with filtering."""
    tenant_id = getattr(request, "tenant_id", "")
    qs = Retainer.objects.filter(tenant_id=tenant_id).select_related("client")
    if client_id:
        qs = qs.filter(client_id=client_id)
    if status:
        qs = qs.filter(status=status)
    return list(qs.order_by("-created_at")[offset : offset + limit])


@router.get("/retainers/{int:retainer_id}", response=RetainerSchema, tags=["Billing"])
def get_retainer(request, retainer_id: int):
    """Get a retainer agreement."""
    tenant_id = getattr(request, "tenant_id", "")
    return get_object_or_404(Retainer, tenant_id=tenant_id, pk=retainer_id)


@router.post("/retainers", response=RetainerSchema, tags=["Billing"])
def create_retainer(request, data: RetainerCreateSchema):
    """Create a new retainer agreement."""
    tenant_id = getattr(request, "tenant_id", "")
    retainer = Retainer.objects.create(
        tenant_id=tenant_id,
        client_id=data.client_id,
        name=data.name,
        monthly_amount=data.monthly_amount,
        monthly_hours=data.monthly_hours,
        start_date=data.start_date,
        end_date=data.end_date,
        renewal_type=data.renewal_type,
        renewal_term_months=data.renewal_term_months,
        auto_invoice=data.auto_invoice,
        invoice_day=data.invoice_day,
        rollover_policy=data.rollover_policy or {},
        overage_rate=data.overage_rate,
        overage_billing_threshold=data.overage_billing_threshold,
        currency=data.currency,
        consumption_alert_thresholds=data.consumption_alert_thresholds or [75, 90, 100],
        notes=data.notes,
        contract_url=data.contract_url or "",
        metadata=data.metadata or {},
    )
    return retainer


@router.put("/retainers/{int:retainer_id}", response=RetainerSchema, tags=["Billing"])
def update_retainer(request, retainer_id: int, data: RetainerUpdateSchema):
    """Update a retainer agreement."""
    tenant_id = getattr(request, "tenant_id", "")
    retainer = get_object_or_404(Retainer, tenant_id=tenant_id, pk=retainer_id)
    for field, value in data.dict(exclude_unset=True).items():
        setattr(retainer, field, value)
    retainer.save()
    return retainer


@router.delete("/retainers/{int:retainer_id}", tags=["Billing"])
def delete_retainer(request, retainer_id: int):
    """Delete a retainer agreement."""
    tenant_id = getattr(request, "tenant_id", "")
    retainer = get_object_or_404(Retainer, tenant_id=tenant_id, pk=retainer_id)
    retainer.delete()
    return {"deleted": True, "retainer_id": retainer_id}


@router.get(
    "/retainers/{int:retainer_id}/consumption",
    response=RetainerConsumptionSchema,
    tags=["Billing"],
)
def get_retainer_consumption(request, retainer_id: int, month: date | None = None):
    """Get monthly consumption for a retainer."""
    tenant_id = getattr(request, "tenant_id", "")
    retainer = get_object_or_404(Retainer, tenant_id=tenant_id, pk=retainer_id)
    if month is None:
        month = date.today()
    usage = calculate_monthly_usage(retainer, month)
    alerts = check_consumption_alerts(retainer, month)
    usage["alerts"] = alerts
    return usage


@router.get(
    "/retainers/{int:retainer_id}/rollover",
    response=RetainerRolloverSchema,
    tags=["Billing"],
)
def get_retainer_rollover(request, retainer_id: int, month: date | None = None):
    """Calculate rollover for a retainer month."""
    tenant_id = getattr(request, "tenant_id", "")
    retainer = get_object_or_404(Retainer, tenant_id=tenant_id, pk=retainer_id)
    if month is None:
        month = date.today()
    return calculate_rollover(retainer, month)


@router.post("/retainers/{int:retainer_id}/renew", response=dict, tags=["Billing"])
def renew_retainer_endpoint(request, retainer_id: int):
    """Renew a retainer agreement."""
    tenant_id = getattr(request, "tenant_id", "")
    retainer = get_object_or_404(Retainer, tenant_id=tenant_id, pk=retainer_id)
    if not should_auto_renew(retainer):
        return {"renewed": False, "reason": "Retainer not eligible for renewal"}
    return renew_retainer(retainer)
