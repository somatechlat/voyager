"""Payment model for Stripe-integrated payment processing.

Tracks payment attempts, refunds, and dunning state.
No card data stored locally — PCI compliance via Stripe.
"""

from __future__ import annotations

from django.db import models

from apps.core.models import TimeStampedModel


class Payment(TimestampedModel):
    """A payment record linked to Stripe."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        PARTIALLY_REFUNDED = "partially_refunded", "Partially Refunded"
        DISPUTED = "disputed", "Disputed"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentMethodType(models.TextChoices):
        CARD = "card", "Card"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"
        ACH = "ach", "ACH"
        WIRE = "wire", "Wire"
        CHECK = "check", "Check"
        CASH = "cash", "Cash"
        OTHER = "other", "Other"

    tenant_id = models.CharField(max_length=128, db_index=True, help_text="Tenant identifier")
    invoice = models.ForeignKey(
        "billing.Invoice",
        on_delete=models.CASCADE,
        related_name="payments",
        blank=True,
        null=True,
        help_text="Invoice this payment is for",
    )
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="payments",
        help_text="The client making the payment",
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2, help_text="Payment amount")
    currency = models.CharField(max_length=3, default="USD", help_text="Currency code")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text="Payment status",
    )
    payment_method_type = models.CharField(
        max_length=20,
        choices=PaymentMethodType.choices,
        default=PaymentMethodType.CARD,
        help_text="Type of payment method",
    )
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
        help_text="Stripe PaymentIntent ID",
    )
    stripe_charge_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Stripe Charge ID",
    )
    stripe_customer_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Stripe Customer ID",
    )
    stripe_payment_method_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Stripe PaymentMethod ID",
    )
    stripe_receipt_url = models.URLField(blank=True, default="", help_text="Stripe receipt URL")
    stripe_refund_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Stripe Refund ID (if refunded)",
    )
    refund_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text="Amount refunded",
    )
    refund_reason = models.TextField(blank=True, help_text="Reason for refund")
    failure_message = models.TextField(blank=True, help_text="Failure reason if payment failed")
    paid_at = models.DateTimeField(blank=True, null=True, help_text="When payment succeeded")
    metadata = models.JSONField(blank=True, default=dict, help_text="Extra payment metadata")

    class Meta:
        db_table = "voyager_payment"
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "client", "-created_at"],
                name="voy_pay_tenant_client_created_idx",
            ),
            models.Index(
                fields=["tenant_id", "status", "-created_at"],
                name="voy_pay_tenant_status_created_idx",
            ),
            models.Index(
                fields=["stripe_payment_intent_id"],
                name="voy_pay_stripe_pi_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Payment {self.amount} {self.currency} - {self.status}"
