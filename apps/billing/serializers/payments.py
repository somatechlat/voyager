"""Ninja schemas for Payment endpoints."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from ninja import Schema


class PaymentCreateSchema(Schema):
    """Schema for creating a payment record."""

    invoice_id: int | None = None
    amount: Decimal
    currency: str = "USD"
    payment_method_type: str = "card"
    stripe_payment_method_id: str = ""
    stripe_customer_id: str = ""


class PaymentRefundSchema(Schema):
    """Schema for refunding a payment."""

    amount: Decimal | None = None
    reason: str = ""


class PaymentListSchema(Schema):
    """Schema for listing payments."""

    id: int
    invoice_id: int | None
    client_id: int
    amount: Decimal
    currency: str
    status: str
    payment_method_type: str
    stripe_payment_intent_id: str
    paid_at: datetime | None
    created_at: datetime


class PaymentSchema(Schema):
    """Full schema for a payment."""

    id: int
    tenant_id: str
    invoice_id: int | None
    client_id: int
    amount: Decimal
    currency: str
    status: str
    payment_method_type: str
    stripe_payment_intent_id: str
    stripe_charge_id: str
    stripe_customer_id: str
    stripe_payment_method_id: str
    stripe_receipt_url: str
    stripe_refund_id: str
    refund_amount: Decimal
    refund_reason: str
    failure_message: str
    paid_at: datetime | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class StripeWebhookSchema(Schema):
    """Schema for Stripe webhook events."""

    id: str = ""
    type: str = ""
    data: dict[str, Any] = {}
    created: int = 0
