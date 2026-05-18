"""Expense model for expense tracking with receipt OCR and approval.

Tracks billable and non-billable expenses with receipt uploads,
categorization, markup, and approval workflow.
"""

from __future__ import annotations

from django.db import models

from .base import TimestampedModel


class Expense(TimestampedModel):
    """A tracked expense."""

    class Category(models.TextChoices):
        TRAVEL = "travel", "Travel"
        MEALS = "meals", "Meals"
        SOFTWARE = "software", "Software"
        ADVERTISING = "advertising", "Advertising"
        SUPPLIES = "supplies", "Supplies"
        PROFESSIONAL_SERVICES = "professional_services", "Professional Services"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        REIMBURSED = "reimbursed", "Reimbursed"
        INVOICED = "invoiced", "Invoiced"
        CANCELLED = "cancelled", "Cancelled"

    tenant_id = models.CharField(max_length=128, db_index=True, help_text="Tenant identifier")
    user_id = models.CharField(
        max_length=128, db_index=True, help_text="User who incurred the expense"
    )
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="expenses",
        blank=True,
        null=True,
        help_text="Client this expense is for",
    )
    project = models.ForeignKey(
        "clients.Project",
        on_delete=models.SET_NULL,
        related_name="expenses",
        blank=True,
        null=True,
        help_text="Project this expense is for",
    )
    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.OTHER,
        db_index=True,
        help_text="Expense category",
    )
    description = models.TextField(help_text="Description of the expense")
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Expense amount")
    currency = models.CharField(max_length=3, default="USD", help_text="Currency code")
    receipt_url = models.URLField(blank=True, default="", help_text="URL to uploaded receipt image")
    receipt_ocr_data = models.JSONField(
        blank=True, default=dict, help_text="OCR-extracted data from receipt"
    )
    ocr_confidence = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        blank=True,
        null=True,
        help_text="OCR extraction confidence (0-1)",
    )
    is_billable = models.BooleanField(
        default=False, help_text="Whether this expense is billable to client"
    )
    markup_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, help_text="Billable markup %"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text="Approval status",
    )
    expense_date = models.DateField(db_index=True, help_text="Date the expense was incurred")
    approver_id = models.CharField(
        max_length=128, blank=True, default="", help_text="Who approved the expense"
    )
    approved_at = models.DateTimeField(
        blank=True, null=True, help_text="When the expense was approved"
    )
    rejection_reason = models.TextField(blank=True, help_text="Reason if rejected")
    vendor = models.CharField(max_length=255, blank=True, default="", help_text="Vendor name")
    invoice = models.ForeignKey(
        "billing.Invoice",
        on_delete=models.SET_NULL,
        related_name="expenses",
        blank=True,
        null=True,
        help_text="Invoice this expense was billed on",
    )
    tags = models.JSONField(blank=True, default=list, help_text="Expense tags")
    metadata = models.JSONField(blank=True, default=dict, help_text="Extra metadata")

    class Meta:
        db_table = "voyager_expense"
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"
        ordering = ["-expense_date"]
        indexes = [
            models.Index(
                fields=["tenant_id", "user_id", "-expense_date"],
                name="voy_exp_tenant_user_date_idx",
            ),
            models.Index(
                fields=["tenant_id", "client", "-expense_date"],
                name="voy_exp_tenant_client_date_idx",
            ),
            models.Index(
                fields=["tenant_id", "status", "category"],
                name="voy_exp_tenant_status_cat_idx",
            ),
            models.Index(
                fields=["tenant_id", "is_billable", "status"],
                name="voy_exp_tenant_billable_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.category} - {self.amount} {self.currency}"
