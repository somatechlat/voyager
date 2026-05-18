"""Payment processing service.

Handles Stripe API integration for payment intents, refunds,
webhook processing, and dunning management.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from django.conf import settings

from apps.billing.models.invoice import Invoice
from apps.billing.models.payment import Payment

logger = logging.getLogger(__name__)

_stripe_module = None


def _get_stripe() -> Any:
    """Lazy-load stripe module.

    Returns:
        The stripe module or None if not installed.
    """
    global _stripe_module
    if _stripe_module is None:
        try:
            import stripe as _stripe_module_import

            _stripe_module = _stripe_module_import
            _stripe_module.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")
        except ImportError:
            logger.warning("stripe module not installed")
            _stripe_module = None
    return _stripe_module


def create_payment_intent(
    invoice: Invoice,
    stripe_customer_id: str = "",
    stripe_payment_method_id: str = "",
) -> dict[str, Any]:
    """Create a Stripe PaymentIntent for an invoice.

    Args:
        invoice: The invoice to charge.
        stripe_customer_id: Optional Stripe customer ID.
        stripe_payment_method_id: Optional Stripe payment method ID.

    Returns:
        Dict with client_secret, payment_intent_id, and status.
    """
    stripe = _get_stripe()
    if stripe is None:
        logger.error("Stripe not available")
        return {"error": "Stripe not available", "client_secret": None}
    try:
        amount_cents = int(invoice.amount_due * 100)
        params: dict[str, Any] = {
            "amount": amount_cents,
            "currency": invoice.currency.lower(),
            "metadata": {
                "invoice_id": str(invoice.pk),
                "invoice_number": invoice.invoice_number,
                "tenant_id": invoice.tenant_id,
                "client_id": str(invoice.client_id),
            },
        }
        if stripe_customer_id:
            params["customer"] = stripe_customer_id
        if stripe_payment_method_id:
            params["payment_method"] = stripe_payment_method_id
            params["confirm"] = True
        intent = stripe.PaymentIntent.create(**params)
        payment = Payment.objects.create(
            tenant_id=invoice.tenant_id,
            invoice=invoice,
            client=invoice.client,
            amount=invoice.amount_due,
            currency=invoice.currency,
            status=Payment.Status.PROCESSING,
            stripe_payment_intent_id=intent.id,
            stripe_customer_id=stripe_customer_id,
            stripe_payment_method_id=stripe_payment_method_id,
        )
        invoice.stripe_payment_intent_id = intent.id
        invoice.save(update_fields=["stripe_payment_intent_id", "updated_at"])
        return {
            "client_secret": intent.client_secret,
            "payment_intent_id": intent.id,
            "status": intent.status,
            "payment_id": payment.pk,
        }
    except Exception as exc:
        logger.exception("Stripe PaymentIntent creation failed")
        return {"error": str(exc), "client_secret": None}


def confirm_payment(payment: Payment) -> dict[str, Any]:
    """Confirm a payment was successful.

    Args:
        payment: The payment to confirm.

    Returns:
        Dict with confirmation result.
    """
    payment.status = Payment.Status.SUCCEEDED
    payment.paid_at = datetime.now()
    payment.save(update_fields=["status", "paid_at", "updated_at"])
    if payment.invoice:
        inv = payment.invoice
        inv.amount_paid = Decimal(str(inv.amount_paid)) + Decimal(str(payment.amount))
        inv.amount_due = Decimal(str(inv.total)) - inv.amount_paid
        if inv.amount_due <= 0:
            inv.status = Invoice.Status.PAID
            inv.paid_at = datetime.now()
        else:
            inv.status = Invoice.Status.PARTIAL
        inv.save(update_fields=["amount_paid", "amount_due", "status", "paid_at", "updated_at"])
    return {
        "payment_id": payment.pk,
        "status": payment.status,
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
    }


def process_refund(
    payment: Payment, amount: Decimal | None = None, reason: str = ""
) -> dict[str, Any]:
    """Process a refund via Stripe.

    Args:
        payment: The payment to refund.
        amount: Refund amount (None for full refund).
        reason: Refund reason.

    Returns:
        Dict with refund result.
    """
    stripe = _get_stripe()
    refund_amount = amount or Decimal(str(payment.amount))
    if stripe and payment.stripe_charge_id:
        try:
            refund_cents = int(refund_amount * 100)
            refund = stripe.Refund.create(
                charge=payment.stripe_charge_id, amount=refund_cents
            )
            payment.stripe_refund_id = refund.id
        except Exception as exc:
            logger.exception("Stripe refund failed")
            return {"error": str(exc), "refunded": False}
    payment.refund_amount = Decimal(str(payment.refund_amount)) + refund_amount
    payment.refund_reason = reason
    if payment.refund_amount >= Decimal(str(payment.amount)):
        payment.status = Payment.Status.REFUNDED
    else:
        payment.status = Payment.Status.PARTIALLY_REFUNDED
    payment.save(update_fields=["refund_amount", "refund_reason", "stripe_refund_id", "status", "updated_at"])
    return {
        "payment_id": payment.pk,
        "refund_amount": str(refund_amount),
        "total_refunded": str(payment.refund_amount),
        "status": payment.status,
    }


def process_webhook_event(event: dict[str, Any]) -> dict[str, Any]:
    """Process a Stripe webhook event.

    Args:
        event: Stripe event dict.

    Returns:
        Dict with processing result.
    """
    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})
    if event_type == "payment_intent.succeeded":
        pi_id = data.get("id", "")
        payment = Payment.objects.filter(stripe_payment_intent_id=pi_id).first()
        if payment:
            confirm_payment(payment)
            return {"processed": True, "event": event_type, "payment_id": payment.pk}
        return {"processed": False, "event": event_type, "reason": "Payment not found"}
    if event_type == "payment_intent.payment_failed":
        pi_id = data.get("id", "")
        payment = Payment.objects.filter(stripe_payment_intent_id=pi_id).first()
        if payment:
            payment.status = Payment.Status.FAILED
            error = data.get("last_payment_error", {})
            payment.failure_message = error.get("message", "")
            payment.save(update_fields=["status", "failure_message", "updated_at"])
            return {"processed": True, "event": event_type, "payment_id": payment.pk}
        return {"processed": False, "event": event_type, "reason": "Payment not found"}
    return {"processed": False, "event": event_type, "reason": "Unhandled event type"}


DUNNING_SCHEDULE: list[dict[str, Any]] = [
    {"day": 1, "action": "send_reminder", "template": "payment_reminder_1"},
    {"day": 7, "action": "send_reminder", "template": "payment_reminder_2"},
    {"day": 14, "action": "send_reminder", "template": "payment_reminder_3", "escalate": True},
    {"day": 30, "action": "suspend_services", "notify": "account_manager"},
    {"day": 60, "action": "send_to_collections", "notify": "finance_team"},
]


def manage_dunning(invoice: Invoice) -> dict[str, Any] | None:
    """Execute dunning actions for an overdue invoice.

    Args:
        invoice: The overdue invoice.

    Returns:
        Dict with action taken, or None if not overdue.
    """
    if invoice.status != Invoice.Status.OVERDUE:
        return None
    if not invoice.due_date:
        return None
    days_overdue = (datetime.now().date() - invoice.due_date).days
    if days_overdue <= 0:
        return None
    current_action = None
    for step in DUNNING_SCHEDULE:
        if step["day"] <= days_overdue:
            current_action = step
    if not current_action:
        return None
    log = list(invoice.dunning_log or [])
    already_taken = any(
        entry.get("day", 0) == current_action["day"] for entry in log
    )
    if already_taken:
        return None
    result = {
        "day": days_overdue,
        "action": current_action["action"],
        "template": current_action.get("template"),
        "escalate": current_action.get("escalate", False),
        "timestamp": datetime.now().isoformat(),
    }
    log.append(result)
    invoice.dunning_log = log
    invoice.save(update_fields=["dunning_log", "updated_at"])
    return result
