"""Project budget views.

API endpoints for budget management, consumption tracking, and forecasting.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.billing.models.project_budget import ProjectBudget
from apps.billing.serializers import (
    BudgetConsumptionSchema,
    BudgetCreateSchema,
    BudgetForecastSchema,
    BudgetListSchema,
    BudgetSchema,
    BudgetUpdateSchema,
)
from apps.billing.services.budgeting import (
    evaluate_budget_alert,
    forecast_budget,
    update_budget_consumption,
)
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/budgets", response=list[BudgetListSchema], tags=["Billing"])
def list_budgets(
    request,
    project_id: int | None = None,
    budget_type: str | None = None,
    alert_level: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List project budgets with filtering."""
    tenant_id = getattr(request, "tenant_id", "")
    qs = ProjectBudget.objects.filter(tenant_id=tenant_id).select_related("project")
    if project_id:
        qs = qs.filter(project_id=project_id)
    if budget_type:
        qs = qs.filter(budget_type=budget_type)
    if alert_level:
        qs = qs.filter(alert_level=alert_level)
    return list(qs.order_by("-created_at")[offset : offset + limit])


@router.get("/budgets/{int:budget_id}", response=BudgetSchema, tags=["Billing"])
def get_budget(request, budget_id: int):
    """Get a single budget."""
    tenant_id = getattr(request, "tenant_id", "")
    return get_object_or_404(ProjectBudget, tenant_id=tenant_id, pk=budget_id)


@router.post("/budgets", response=BudgetSchema, tags=["Billing"])
def create_budget(request, data: BudgetCreateSchema):
    """Create a new project budget."""
    tenant_id = getattr(request, "tenant_id", "")
    budget = ProjectBudget.objects.create(
        tenant_id=tenant_id,
        project_id=data.project_id,
        budget_type=data.budget_type,
        total_budget=data.total_budget,
        hours_allocated=data.hours_allocated,
        hourly_rate=data.hourly_rate,
        monthly_retainer=data.monthly_retainer,
        base_retainer=data.base_retainer,
        overage_rate=data.overage_rate,
        start_date=data.start_date,
        end_date=data.end_date,
        currency=data.currency,
    )
    return budget


@router.put("/budgets/{int:budget_id}", response=BudgetSchema, tags=["Billing"])
def update_budget(request, budget_id: int, data: BudgetUpdateSchema):
    """Update a project budget."""
    tenant_id = getattr(request, "tenant_id", "")
    budget = get_object_or_404(ProjectBudget, tenant_id=tenant_id, pk=budget_id)
    for field, value in data.dict(exclude_unset=True).items():
        setattr(budget, field, value)
    budget.save()
    return budget


@router.delete("/budgets/{int:budget_id}", tags=["Billing"])
def delete_budget(request, budget_id: int):
    """Delete a project budget."""
    tenant_id = getattr(request, "tenant_id", "")
    budget = get_object_or_404(ProjectBudget, tenant_id=tenant_id, pk=budget_id)
    budget.delete()
    return {"deleted": True, "budget_id": budget_id}


@router.post("/budgets/{int:budget_id}/consume", response=dict, tags=["Billing"])
def consume_budget(
    request, budget_id: int, amount: float, hours: float = 0
):
    """Record consumption against a budget."""
    tenant_id = getattr(request, "tenant_id", "")
    budget = get_object_or_404(ProjectBudget, tenant_id=tenant_id, pk=budget_id)
    from decimal import Decimal

    result = update_budget_consumption(
        budget, Decimal(str(amount)), Decimal(str(hours))
    )
    return result


@router.get("/budgets/{int:budget_id}/forecast", response=BudgetForecastSchema, tags=["Billing"])
def get_budget_forecast(request, budget_id: int):
    """Get budget forecast."""
    tenant_id = getattr(request, "tenant_id", "")
    budget = get_object_or_404(ProjectBudget, tenant_id=tenant_id, pk=budget_id)
    result = forecast_budget(budget)
    return result


@router.get("/budgets/{int:budget_id}/alert", response=dict, tags=["Billing"])
def get_budget_alert(request, budget_id: int):
    """Get budget alert status."""
    tenant_id = getattr(request, "tenant_id", "")
    budget = get_object_or_404(ProjectBudget, tenant_id=tenant_id, pk=budget_id)
    return evaluate_budget_alert(budget)
