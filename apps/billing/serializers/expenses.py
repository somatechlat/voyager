"""Ninja schemas for Expense endpoints."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from ninja import Schema


class ExpenseCreateSchema(Schema):
    """Schema for creating an expense."""

    user_id: str
    client_id: int | None = None
    project_id: int | None = None
    category: str = "other"
    description: str
    amount: Decimal
    currency: str = "USD"
    is_billable: bool = False
    markup_pct: Decimal = Decimal("0")
    expense_date: date
    vendor: str = ""
    receipt_url: str = ""


class ExpenseUpdateSchema(Schema):
    """Schema for updating an expense."""

    category: str | None = None
    description: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    is_billable: bool | None = None
    markup_pct: Decimal | None = None
    status: str | None = None
    vendor: str | None = None
    receipt_url: str | None = None
    tags: list[str] | None = None


class ExpenseListSchema(Schema):
    """Schema for listing expenses."""

    id: int
    user_id: str
    client_id: int | None
    project_id: int | None
    category: str
    description: str
    amount: Decimal
    currency: str
    is_billable: bool
    markup_pct: Decimal
    status: str
    expense_date: date
    created_at: datetime


class ExpenseSchema(Schema):
    """Full schema for an expense."""

    id: int
    tenant_id: str
    user_id: str
    client_id: int | None
    project_id: int | None
    category: str
    description: str
    amount: Decimal
    currency: str
    receipt_url: str
    receipt_ocr_data: dict[str, Any]
    ocr_confidence: Decimal | None
    is_billable: bool
    markup_pct: Decimal
    status: str
    expense_date: date
    approver_id: str
    approved_at: datetime | None
    rejection_reason: str
    vendor: str
    tags: list[str]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ExpenseOCRSchema(Schema):
    """Schema for OCR processing result."""

    vendor: str
    date: str | None
    total: str | None
    currency: str
    category: str
    confidence: str


class ExpenseApprovalSchema(Schema):
    """Schema for expense approval/rejection result."""

    expense_id: int
    status: str
    approved_by: str | None = None
    approved_at: str | None = None
    reason: str = ""
    rejected_by: str | None = None
