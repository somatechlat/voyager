"""Invoicing service.

Handles invoice generation from time entries, expenses, and retainers,
tax calculation, numbering, and lifecycle management.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db import transaction

from apps.billing.models.expense import Expense
from apps.billing.models.invoice import Invoice
from apps.billing.models.line_item import LineItem
from apps.billing.models.retainer import Retainer
from apps.billing.models.time_entry import TimeEntry


def generate_invoice_number(tenant_id: str) -> str:
    """Generate a unique invoice number.

    Args:
        tenant_id: Tenant identifier.

    Returns:
        Unique invoice number string.
    """
    prefix = "INV"
    today_str = date.today().strftime("%Y%m%d")
    suffix = uuid.uuid4().hex[:8].upper()
    return f"{prefix}-{today_str}-{suffix}"


def calculate_line_item_amount(quantity: Decimal, rate: Decimal | None) -> Decimal:
    """Calculate line item amount.

    Args:
        quantity: Quantity.
        rate: Rate per unit.

    Returns:
        Calculated amount.
    """
    if rate is None:
        return Decimal("0")
    return Decimal(str(round(quantity * rate, 2)))


def build_time_line_items(
    tenant_id: str, client_id: int, date_from: date, date_to: date
) -> list[dict[str, Any]]:
    """Build line items from unbilled time entries.

    Args:
        tenant_id: Tenant identifier.
        client_id: Client ID.
        date_from: Start date.
        date_to: End date.

    Returns:
        List of line item dicts.
    """
    entries = TimeEntry.objects.filter(
        tenant_id=tenant_id,
        client_id=client_id,
        started_at__date__gte=date_from,
        started_at__date__lte=date_to,
        status=TimeEntry.Status.APPROVED,
        is_billable=True,
        invoice__isnull=True,
    ).select_related("project")
    grouped: dict[str, dict[str, Any]] = {}
    for e in entries:
        key = f"{e.project_id or 'no-project'}|{e.task_name or 'General'}"
        rate = e.billing_rate or Decimal("0")
        hours = Decimal(str(e.rounded_minutes)) / Decimal("60")
        if key not in grouped:
            grouped[key] = {
                "type": "time",
                "description": f"{e.project.name if e.project else 'General'} - {e.task_name or 'General'}",
                "quantity": Decimal("0"),
                "unit": "hours",
                "rate": rate,
                "project_id": e.project_id,
                "amount": Decimal("0"),
            }
        grouped[key]["quantity"] += hours
        grouped[key]["amount"] += calculate_line_item_amount(hours, rate)
    return [
        {
            "type": v["type"],
            "description": v["description"],
            "quantity": round(v["quantity"], 2),
            "unit": v["unit"],
            "rate": str(v["rate"]),
            "amount": str(round(v["amount"], 2)),
            "project_id": v["project_id"],
        }
        for v in grouped.values()
    ]


def build_expense_line_items(
    tenant_id: str, client_id: int, date_from: date, date_to: date
) -> list[dict[str, Any]]:
    """Build line items from unbilled expenses.

    Args:
        tenant_id: Tenant identifier.
        client_id: Client ID.
        date_from: Start date.
        date_to: End date.

    Returns:
        List of line item dicts.
    """
    expenses = Expense.objects.filter(
        tenant_id=tenant_id,
        client_id=client_id,
        expense_date__gte=date_from,
        expense_date__lte=date_to,
        status=Expense.Status.APPROVED,
        is_billable=True,
        invoice__isnull=True,
    )
    result = []
    for exp in expenses:
        rate = exp.amount * (Decimal("1") + exp.markup_pct / Decimal("100"))
        result.append(
            {
                "type": "expense",
                "description": f"{exp.category}: {exp.description}",
                "quantity": Decimal("1"),
                "unit": "item",
                "rate": str(round(rate, 2)),
                "amount": str(round(rate, 2)),
                "expense_id": exp.pk,
            }
        )
    return result


def build_retainer_line_items(
    tenant_id: str, client_id: int, billing_month: date
) -> list[dict[str, Any]]:
    """Build line items from active retainers.

    Args:
        tenant_id: Tenant identifier.
        client_id: Client ID.
        billing_month: Month to bill for.

    Returns:
        List of line item dicts.
    """
    retainers = Retainer.objects.filter(
        tenant_id=tenant_id,
        client_id=client_id,
        status=Retainer.Status.ACTIVE,
    )
    result = []
    month_label = billing_month.strftime("%B %Y")
    for ret in retainers:
        result.append(
            {
                "type": "retainer",
                "description": f"Monthly retainer - {month_label}",
                "quantity": Decimal("1"),
                "unit": "month",
                "rate": str(ret.monthly_amount),
                "amount": str(ret.monthly_amount),
                "retainer_id": ret.pk,
            }
        )
    return result


def calculate_tax(subtotal: Decimal, tax_rates: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate tax on a subtotal.

    Args:
        subtotal: Amount before tax.
        tax_rates: List of rate dicts with 'name', 'rate'.

    Returns:
        Dict with subtotal, taxes, total_tax, total.
    """
    taxes = []
    total_tax = Decimal("0")
    for tr in tax_rates:
        rate_pct = Decimal(str(tr.get("rate", 0)))
        tax_amount = Decimal(str(round(subtotal * rate_pct / Decimal("100"), 2)))
        taxes.append({"name": tr.get("name", ""), "rate": str(rate_pct), "amount": str(tax_amount)})
        total_tax += tax_amount
    return {
        "subtotal": str(subtotal),
        "taxes": taxes,
        "total_tax": str(total_tax),
        "total": str(subtotal + total_tax),
    }


def create_invoice(
    tenant_id: str,
    client_id: int,
    date_from: date,
    date_to: date,
    invoice_type: str = "standard",
    tax_rates: list[dict[str, Any]] | None = None,
    currency: str = "USD",
    notes: str = "",
    payment_terms: str = "net_30",
    payment_terms_days: int = 30,
    template: str = "default",
    auto_send: bool = False,
) -> Invoice:
    """Create an invoice from unbilled items.

    Args:
        tenant_id: Tenant identifier.
        client_id: Client ID.
        date_from: Billing period start.
        date_to: Billing period end.
        invoice_type: Type of invoice.
        tax_rates: Tax rate configuration.
        currency: Currency code.
        notes: Invoice notes.
        payment_terms: Payment terms code.
        payment_terms_days: Days until due.
        template: Template name.
        auto_send: Whether to auto-send.

    Returns:
        Created Invoice instance.
    """
    with transaction.atomic():
        line_data = build_time_line_items(tenant_id, client_id, date_from, date_to)
        line_data += build_expense_line_items(tenant_id, client_id, date_from, date_to)
        if invoice_type == "retainer":
            line_data += build_retainer_line_items(tenant_id, client_id, date_from)
        subtotal = Decimal("0")
        for li in line_data:
            subtotal += Decimal(str(li["amount"]))
        tax_rates = tax_rates or []
        tax = calculate_tax(subtotal, tax_rates)
        invoice_date = date.today()
        due_date = invoice_date + timedelta(days=payment_terms_days)
        invoice = Invoice.objects.create(
            tenant_id=tenant_id,
            client_id=client_id,
            invoice_number=generate_invoice_number(tenant_id),
            status=Invoice.Status.DRAFT,
            invoice_type=invoice_type,
            subtotal=subtotal,
            tax_amount=Decimal(str(tax["total_tax"])),
            total=Decimal(str(tax["total"])),
            amount_due=Decimal(str(tax["total"])),
            currency=currency,
            invoice_date=invoice_date,
            due_date=due_date,
            payment_terms=payment_terms,
            payment_terms_days=payment_terms_days,
            notes=notes,
            template=template,
            auto_send=auto_send,
            date_from=date_from,
            date_to=date_to,
        )
        for idx, li in enumerate(line_data):
            LineItem.objects.create(
                tenant_id=tenant_id,
                invoice=invoice,
                item_type=li["type"],
                description=li["description"],
                quantity=Decimal(str(li["quantity"])),
                unit=li["unit"],
                rate=Decimal(str(li["rate"])) if li["rate"] else None,
                amount=Decimal(str(li["amount"])),
                project_id=li.get("project_id"),
                expense_id=li.get("expense_id"),
                retainer_id=li.get("retainer_id"),
                sort_order=idx,
            )
        return invoice
