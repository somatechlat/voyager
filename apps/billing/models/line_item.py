"""LineItem model for invoice line items.

Each line item represents a chargeable entry on an invoice:
time-based, expense-based, retainer, or custom.
"""

from __future__ import annotations

from django.db import models

from apps.core.models import TimeStampedModel


class LineItem(TimestampedModel):
    """A single line item on an invoice."""

    class ItemType(models.TextChoices):
        TIME = "time", "Time"
        EXPENSE = "expense", "Expense"
        RETAINER = "retainer", "Retainer"
        CUSTOM = "custom", "Custom"
        DISCOUNT = "discount", "Discount"

    tenant_id = models.CharField(max_length=128, db_index=True, help_text="Tenant identifier")
    invoice = models.ForeignKey(
        "billing.Invoice",
        on_delete=models.CASCADE,
        related_name="line_items_set",
        help_text="The invoice this line item belongs to",
    )
    item_type = models.CharField(
        max_length=20,
        choices=ItemType.choices,
        default=ItemType.TIME,
        db_index=True,
        help_text="Type of line item",
    )
    description = models.TextField(help_text="Description shown on invoice")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1, help_text="Quantity")
    unit = models.CharField(max_length=20, default="hours", help_text="Unit of measure")
    rate = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Rate per unit",
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="Total amount (quantity * rate)"
    )
    project = models.ForeignKey(
        "clients.Project",
        on_delete=models.SET_NULL,
        related_name="line_items",
        blank=True,
        null=True,
        help_text="Project this line item relates to",
    )
    time_entry = models.ForeignKey(
        "billing.TimeEntry",
        on_delete=models.SET_NULL,
        related_name="line_items",
        blank=True,
        null=True,
        help_text="Linked time entry",
    )
    expense = models.ForeignKey(
        "billing.Expense",
        on_delete=models.SET_NULL,
        related_name="line_items",
        blank=True,
        null=True,
        help_text="Linked expense",
    )
    retainer = models.ForeignKey(
        "billing.Retainer",
        on_delete=models.SET_NULL,
        related_name="line_items",
        blank=True,
        null=True,
        help_text="Linked retainer",
    )
    sort_order = models.PositiveIntegerField(default=0, help_text="Display order on invoice")
    tax_applicable = models.BooleanField(default=True, help_text="Whether tax applies to this line")
    metadata = models.JSONField(
        blank=True, default=dict, help_text="Extra data (task name, dates, etc.)"
    )

    class Meta:
        db_table = "voyager_line_item"
        verbose_name = "Line Item"
        verbose_name_plural = "Line Items"
        ordering = ["invoice", "sort_order", "created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "invoice", "sort_order"],
                name="voy_li_tenant_invoice_sort_idx",
            ),
            models.Index(
                fields=["tenant_id", "item_type"],
                name="voy_li_tenant_type_idx",
            ),
            models.Index(
                fields=["tenant_id", "project"],
                name="voy_li_tenant_project_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.description} - {self.amount}"
