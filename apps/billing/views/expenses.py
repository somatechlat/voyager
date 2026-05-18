"""Expense views.

API endpoints for expense tracking, receipt OCR, and approval workflow.
"""

from __future__ import annotations

from datetime import date

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.billing.models.expense import Expense
from apps.billing.serializers import (
    ExpenseApprovalSchema,
    ExpenseCreateSchema,
    ExpenseListSchema,
    ExpenseOCRSchema,
    ExpenseSchema,
    ExpenseUpdateSchema,
)
from apps.billing.services.expenses import (
    approve_expense,
    calculate_billable_amount,
    process_receipt_ocr,
    reject_expense,
)
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/expenses", response=list[ExpenseListSchema], tags=["Billing"])
def list_expenses(
    request,
    client_id: int | None = None,
    user_id: str | None = None,
    category: str | None = None,
    status: str | None = None,
    is_billable: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List expenses with filtering."""
    tenant_id = getattr(request, "tenant_id", "")
    qs = Expense.objects.filter(tenant_id=tenant_id)
    if client_id:
        qs = qs.filter(client_id=client_id)
    if user_id:
        qs = qs.filter(user_id=user_id)
    if category:
        qs = qs.filter(category=category)
    if status:
        qs = qs.filter(status=status)
    if is_billable is not None:
        qs = qs.filter(is_billable=is_billable)
    if date_from:
        qs = qs.filter(expense_date__gte=date_from)
    if date_to:
        qs = qs.filter(expense_date__lte=date_to)
    return list(qs.order_by("-expense_date")[offset : offset + limit])


@router.get("/expenses/{int:expense_id}", response=ExpenseSchema, tags=["Billing"])
def get_expense(request, expense_id: int):
    """Get a single expense."""
    tenant_id = getattr(request, "tenant_id", "")
    return get_object_or_404(Expense, tenant_id=tenant_id, pk=expense_id)


@router.post("/expenses", response=ExpenseSchema, tags=["Billing"])
def create_expense(request, data: ExpenseCreateSchema):
    """Create a new expense."""
    tenant_id = getattr(request, "tenant_id", "")
    expense = Expense.objects.create(
        tenant_id=tenant_id,
        user_id=data.user_id,
        client_id=data.client_id,
        project_id=data.project_id,
        category=data.category,
        description=data.description,
        amount=data.amount,
        currency=data.currency,
        is_billable=data.is_billable,
        markup_pct=data.markup_pct,
        expense_date=data.expense_date,
        vendor=data.vendor,
        receipt_url=data.receipt_url or "",
    )
    return expense


@router.put("/expenses/{int:expense_id}", response=ExpenseSchema, tags=["Billing"])
def update_expense(request, expense_id: int, data: ExpenseUpdateSchema):
    """Update an expense."""
    tenant_id = getattr(request, "tenant_id", "")
    expense = get_object_or_404(Expense, tenant_id=tenant_id, pk=expense_id)
    for field, value in data.dict(exclude_unset=True).items():
        setattr(expense, field, value)
    expense.save()
    return expense


@router.delete("/expenses/{int:expense_id}", tags=["Billing"])
def delete_expense(request, expense_id: int):
    """Delete an expense."""
    tenant_id = getattr(request, "tenant_id", "")
    expense = get_object_or_404(Expense, tenant_id=tenant_id, pk=expense_id)
    expense.delete()
    return {"deleted": True, "expense_id": expense_id}


@router.post("/expenses/ocr", response=ExpenseOCRSchema, tags=["Billing"])
def process_ocr(request, ocr_text: str):
    """Process receipt OCR text and return structured data."""
    result = process_receipt_ocr(ocr_text)
    return result


@router.post("/expenses/{int:expense_id}/approve", response=ExpenseApprovalSchema, tags=["Billing"])
def approve_expense_endpoint(request, expense_id: int, notes: str = ""):
    """Approve an expense."""
    tenant_id = getattr(request, "tenant_id", "")
    approver_id = getattr(request, "user_id", "")
    expense = get_object_or_404(Expense, tenant_id=tenant_id, pk=expense_id)
    result = approve_expense(expense, approver_id, notes)
    return result


@router.post("/expenses/{int:expense_id}/reject", response=ExpenseApprovalSchema, tags=["Billing"])
def reject_expense_endpoint(request, expense_id: int, reason: str = ""):
    """Reject an expense."""
    tenant_id = getattr(request, "tenant_id", "")
    approver_id = getattr(request, "user_id", "")
    expense = get_object_or_404(Expense, tenant_id=tenant_id, pk=expense_id)
    result = reject_expense(expense, approver_id, reason)
    return result


@router.get("/expenses/{int:expense_id}/billable-amount", response=dict, tags=["Billing"])
def get_billable_amount(request, expense_id: int):
    """Get the billable amount for an expense."""
    tenant_id = getattr(request, "tenant_id", "")
    expense = get_object_or_404(Expense, tenant_id=tenant_id, pk=expense_id)
    amount = calculate_billable_amount(expense)
    return {"expense_id": expense_id, "billable_amount": str(amount)}
