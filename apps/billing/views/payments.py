"""Payment views.

API endpoints for Stripe payment processing, refund handling,
webhook processing, and dunning management.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.billing.models.invoice import Invoice
from apps.billing.models.payment import Payment
from apps.billing.serializers import (
    PaymentCreateSchema,
    PaymentListSchema,
    PaymentRefundSchema,
    PaymentSchema,
    StripeWebhookSchema,
)
from apps.billing.services.payments import (
    confirm_payment,
    create_payment_intent,
    manage_dunning,
    process_refund,
    process_webhook_event,
)
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/payments", response=list[PaymentListSchema], tags=["Billing"])
def list_payments(
    request,
    client_id: int | None = None,
    invoice_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List payments with filtering."""
    tenant_id = getattr(request, "tenant_id", "")
    qs = Payment.objects.filter(tenant_id=tenant_id).select_related("invoice", "client")
    if client_id:
        qs = qs.filter(client_id=client_id)
    if invoice_id:
        qs = qs.filter(invoice_id=invoice_id)
    if status:
        qs = qs.filter(status=status)
    return list(qs.order_by("-created_at")[offset : offset + limit])


@router.get("/payments/{int:payment_id}", response=PaymentSchema, tags=["Billing"])
def get_payment(request, payment_id: int):
    """Get a payment record."""
    tenant_id = getattr(request, "tenant_id", "")
    return get_object_or_404(Payment, tenant_id=tenant_id, pk=payment_id)


@router.post(
    "/invoices/{int:invoice_id}/pay",
    response=dict,
    tags=["Billing"],
)
def pay_invoice(
    request,
    invoice_id: int,
    stripe_customer_id: str = "",
    stripe_payment_method_id: str = "",
):
    """Create a payment intent for an invoice."""
    tenant_id = getattr(request, "tenant_id", "")
    invoice = get_object_or_404(Invoice, tenant_id=tenant_id, pk=invoice_id)
    result = create_payment_intent(invoice, stripe_customer_id, stripe_payment_method_id)
    return result


@router.post("/payments/{int:payment_id}/confirm", response=dict, tags=["Billing"])
def confirm_payment_endpoint(request, payment_id: int):
    """Confirm a payment as successful."""
    tenant_id = getattr(request, "tenant_id", "")
    payment = get_object_or_404(Payment, tenant_id=tenant_id, pk=payment_id)
    return confirm_payment(payment)


@router.post(
    "/payments/{int:payment_id}/refund", response=dict, tags=["Billing"]
)
def refund_payment(request, payment_id: int, data: PaymentRefundSchema):
    """Process a refund for a payment."""
    tenant_id = getattr(request, "tenant_id", "")
    payment = get_object_or_404(Payment, tenant_id=tenant_id, pk=payment_id)
    amount = Decimal(str(data.amount)) if data.amount else None
    return process_refund(payment, amount, data.reason)


@router.post("/payments/stripe-webhook", tags=["Billing"], auth=None)
def stripe_webhook(request, data: StripeWebhookSchema):
    """Process Stripe webhook events.

    Public endpoint (no auth) as called by Stripe servers.
    Signature verification should be handled by middleware.
    """
    result = process_webhook_event(data.dict())
    return result


@router.get(
    "/invoices/{int:invoice_id}/dunning", response=dict | None, tags=["Billing"]
)
def get_dunning_action(request, invoice_id: int):
    """Evaluate and execute dunning for an overdue invoice."""
    tenant_id = getattr(request, "tenant_id", "")
    invoice = get_object_or_404(Invoice, tenant_id=tenant_id, pk=invoice_id)
    result = manage_dunning(invoice)
    if result is None:
        return {"action_taken": False, "reason": "No dunning action needed"}
    return {"action_taken": True, "dunning_action": result}
