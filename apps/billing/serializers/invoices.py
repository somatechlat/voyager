"""Ninja schemas for Invoice and Line Item endpoints."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from ninja import Schema

from apps.billing.serializers.base import TaxRateSchema


class InvoiceCreateSchema(Schema):
    """Schema for generating an invoice."""

    client_id: int
    date_from: date
    date_to: date
    invoice_type: str = "standard"
    tax_rates: list[TaxRateSchema] | None = None
    currency: str = "USD"
    notes: str = ""
    payment_terms: str = "net_30"
    payment_terms_days: int = 30
    template: str = "default"
    auto_send: bool = False


class InvoiceUpdateSchema(Schema):
    """Schema for updating an invoice."""

    notes: str | None = None
    internal_notes: str | None = None
    payment_terms_days: int | None = None
    auto_send: bool | None = None


class InvoiceStatusUpdateSchema(Schema):
    """Schema for updating invoice status."""

    status: str


class InvoiceListSchema(Schema):
    """Schema for listing invoices."""

    id: int
    client_id: int
    invoice_number: str
    status: str
    invoice_type: str
    subtotal: Decimal
    total: Decimal
    amount_due: Decimal
    currency: str
    invoice_date: date
    due_date: date
    created_at: datetime


class InvoiceSchema(Schema):
    """Full schema for an invoice."""

    id: int
    tenant_id: str
    client_id: int
    invoice_number: str
    status: str
    invoice_type: str
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    currency: str
    exchange_rate: Decimal
    invoice_date: date
    due_date: date
    paid_at: datetime | None
    payment_terms: str
    payment_terms_days: int
    payment_method: str
    stripe_payment_intent_id: str
    notes: str
    internal_notes: str
    dunning_log: list[dict[str, Any]]
    date_from: date | None
    date_to: date | None
    sent_at: datetime | None
    auto_send: bool
    created_at: datetime
    updated_at: datetime


class LineItemCreateSchema(Schema):
    """Schema for creating a line item."""

    item_type: str = "custom"
    description: str
    quantity: Decimal = Decimal("1")
    unit: str = "item"
    rate: Decimal | None = None
    amount: Decimal
    project_id: int | None = None
    tax_applicable: bool = True


class LineItemSchema(Schema):
    """Schema for a line item."""

    id: int
    tenant_id: str
    invoice_id: int
    item_type: str
    description: str
    quantity: Decimal
    unit: str
    rate: Decimal | None
    amount: Decimal
    project_id: int | None
    sort_order: int
    tax_applicable: bool
    created_at: datetime
