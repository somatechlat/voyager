"""Invoice model for billing document generation and lifecycle.

Tracks invoice status from draft through paid, with line items,
tax calculation, multi-currency, and dunning management.
"""

from __future__ import annotations

from django.db import models

from apps.core.models import TimeStampedModel


class Invoice(TimestampedModel):
    """A billing invoice."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        VIEWED = "viewed", "Viewed"
        PARTIAL = "partial", "Partially Paid"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"
        VOID = "void", "Void"
        WRITTEN_OFF = "written_off", "Written Off"

    class PaymentTerms(models.TextChoices):
        NET_15 = "net_15", "Net 15"
        NET_30 = "net_30", "Net 30"
        NET_60 = "net_60", "Net 60"
        DUE_ON_RECEIPT = "due_on_receipt", "Due on Receipt"
        CUSTOM = "custom", "Custom"

    tenant_id = models.CharField(max_length=128, db_index=True, help_text="Tenant identifier")
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="invoices",
        help_text="The client being billed",
    )
    invoice_number = models.CharField(
        max_length=50, unique=True, db_index=True, help_text="Unique invoice number"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text="Current invoice status",
    )
    invoice_type = models.CharField(
        max_length=20,
        default="standard",
        db_index=True,
        help_text="Invoice type: standard, retainer, recurring",
    )
    subtotal = models.DecimalField(
        max_digits=14, decimal_places=2, help_text="Sum of line items before tax"
    )
    tax_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, help_text="Total tax amount"
    )
    total = models.DecimalField(
        max_digits=14, decimal_places=2, help_text="Final total including tax"
    )
    amount_paid = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, help_text="Amount paid so far"
    )
    amount_due = models.DecimalField(
        max_digits=14, decimal_places=2, help_text="Remaining amount due"
    )
    currency = models.CharField(max_length=3, default="USD", help_text="Currency code (ISO 4217)")
    exchange_rate = models.DecimalField(
        max_digits=14,
        decimal_places=6,
        default=1,
        help_text="Exchange rate to base currency",
    )
    invoice_date = models.DateField(db_index=True, help_text="Date the invoice was issued")
    due_date = models.DateField(db_index=True, help_text="Date payment is due")
    paid_at = models.DateTimeField(
        blank=True, null=True, help_text="When the invoice was fully paid"
    )
    payment_terms = models.CharField(
        max_length=20,
        choices=PaymentTerms.choices,
        default=PaymentTerms.NET_30,
        help_text="Payment terms for this invoice",
    )
    payment_terms_days = models.PositiveIntegerField(
        default=30, help_text="Number of days until due"
    )
    payment_method = models.CharField(
        max_length=50, blank=True, default="", help_text="Method used for payment"
    )
    stripe_payment_intent_id = models.CharField(
        max_length=255, blank=True, default="", help_text="Stripe PaymentIntent ID"
    )
    stripe_invoice_id = models.CharField(
        max_length=255, blank=True, default="", help_text="Stripe Invoice ID"
    )
    template = models.CharField(
        max_length=50,
        default="default",
        help_text="Invoice template name",
    )
    notes = models.TextField(blank=True, help_text="Notes visible to the client")
    internal_notes = models.TextField(blank=True, help_text="Internal-only notes")
    dunning_log = models.JSONField(default=list, help_text="Dunning management log entries")
    date_from = models.DateField(blank=True, null=True, help_text="Start of billing period")
    date_to = models.DateField(blank=True, null=True, help_text="End of billing period")
    sent_at = models.DateTimeField(blank=True, null=True, help_text="When the invoice was sent")
    sent_to = models.JSONField(
        blank=True, default=list, help_text="Email addresses the invoice was sent to"
    )
    auto_send = models.BooleanField(default=False, help_text="Whether to auto-send this invoice")
    reminder_schedule = models.JSONField(
        blank=True, default=dict, help_text="Custom reminder schedule"
    )

    class Meta:
        db_table = "voyager_invoice"
        verbose_name = "Invoice"
        verbose_name_plural = "Invoices"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "client", "-created_at"],
                name="voy_inv_tenant_client_created_idx",
            ),
            models.Index(
                fields=["tenant_id", "status", "due_date"],
                name="voy_inv_tenant_status_due_idx",
            ),
            models.Index(
                fields=["tenant_id", "invoice_type", "status"],
                name="voy_inv_tenant_type_status_idx",
            ),
            models.Index(
                fields=["tenant_id", "invoice_date"],
                name="voy_inv_tenant_date_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Invoice {self.invoice_number} - {self.client.name}"
