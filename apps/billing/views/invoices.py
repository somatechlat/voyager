"""Invoice views.

API endpoints for invoice generation, management, sending, and payment.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.billing.models.invoice import Invoice
from apps.billing.models.line_item import LineItem
from apps.billing.serializers import (
    InvoiceCreateSchema,
    InvoiceListSchema,
    InvoiceSchema,
    InvoiceStatusUpdateSchema,
    InvoiceUpdateSchema,
    LineItemCreateSchema,
    LineItemSchema,
)
from apps.billing.services.invoicing import create_invoice
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/invoices", response=list[InvoiceListSchema], tags=["Billing"])
def list_invoices(
    request,
    client_id: int | None = None,
    status: str | None = None,
    invoice_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List invoices with filtering."""
    tenant_id = getattr(request, "tenant_id", "")
    qs = Invoice.objects.filter(tenant_id=tenant_id).select_related("client")
    if client_id:
        qs = qs.filter(client_id=client_id)
    if status:
        qs = qs.filter(status=status)
    if invoice_type:
        qs = qs.filter(invoice_type=invoice_type)
    if date_from:
        qs = qs.filter(invoice_date__gte=date_from)
    if date_to:
        qs = qs.filter(invoice_date__lte=date_to)
    return list(qs.order_by("-created_at")[offset : offset + limit])


@router.get("/invoices/{int:invoice_id}", response=InvoiceSchema, tags=["Billing"])
def get_invoice(request, invoice_id: int):
    """Get a single invoice with line items."""
    tenant_id = getattr(request, "tenant_id", "")
    return get_object_or_404(Invoice, tenant_id=tenant_id, pk=invoice_id)


@router.post("/invoices", response=InvoiceSchema, tags=["Billing"])
def generate_invoice_endpoint(request, data: InvoiceCreateSchema):
    """Generate an invoice from unbilled items."""
    tenant_id = getattr(request, "tenant_id", "")
    tax_rates = []
    if data.tax_rates:
        tax_rates = [tr.dict() for tr in data.tax_rates]
    invoice = create_invoice(
        tenant_id=tenant_id,
        client_id=data.client_id,
        date_from=data.date_from,
        date_to=data.date_to,
        invoice_type=data.invoice_type,
        tax_rates=tax_rates,
        currency=data.currency,
        notes=data.notes,
        payment_terms=data.payment_terms,
        payment_terms_days=data.payment_terms_days,
        template=data.template,
        auto_send=data.auto_send,
    )
    return invoice


@router.put("/invoices/{int:invoice_id}", response=InvoiceSchema, tags=["Billing"])
def update_invoice(request, invoice_id: int, data: InvoiceUpdateSchema):
    """Update an invoice."""
    tenant_id = getattr(request, "tenant_id", "")
    invoice = get_object_or_404(Invoice, tenant_id=tenant_id, pk=invoice_id)
    for field, value in data.dict(exclude_unset=True).items():
        setattr(invoice, field, value)
    invoice.save()
    return invoice


@router.post("/invoices/{int:invoice_id}/status", response=InvoiceSchema, tags=["Billing"])
def update_invoice_status(request, invoice_id: int, data: InvoiceStatusUpdateSchema):
    """Update invoice status."""
    tenant_id = getattr(request, "tenant_id", "")
    invoice = get_object_or_404(Invoice, tenant_id=tenant_id, pk=invoice_id)
    invoice.status = data.status
    if data.status == Invoice.Status.SENT and not invoice.sent_at:
        from django.utils import timezone

        invoice.sent_at = timezone.now()
    if data.status == Invoice.Status.VOID:
        invoice.amount_due = Decimal("0")
    invoice.save()
    return invoice


@router.delete("/invoices/{int:invoice_id}", tags=["Billing"])
def delete_invoice(request, invoice_id: int):
    """Delete a draft invoice."""
    tenant_id = getattr(request, "tenant_id", "")
    invoice = get_object_or_404(Invoice, tenant_id=tenant_id, pk=invoice_id)
    invoice.delete()
    return {"deleted": True, "invoice_id": invoice_id}


@router.get(
    "/invoices/{int:invoice_id}/line-items",
    response=list[LineItemSchema],
    tags=["Billing"],
)
def list_invoice_line_items(request, invoice_id: int):
    """List line items for an invoice."""
    tenant_id = getattr(request, "tenant_id", "")
    return list(
        LineItem.objects.filter(tenant_id=tenant_id, invoice_id=invoice_id).order_by(
            "sort_order", "created_at"
        )
    )


@router.post(
    "/invoices/{int:invoice_id}/line-items",
    response=LineItemSchema,
    tags=["Billing"],
)
def add_line_item(request, invoice_id: int, data: LineItemCreateSchema):
    """Add a line item to an invoice."""
    tenant_id = getattr(request, "tenant_id", "")
    invoice = get_object_or_404(Invoice, tenant_id=tenant_id, pk=invoice_id)
    max_order = (
        LineItem.objects.filter(invoice=invoice)
        .order_by("-sort_order")
        .values_list("sort_order", flat=True)
        .first()
        or 0
    )
    item = LineItem.objects.create(
        tenant_id=tenant_id,
        invoice=invoice,
        item_type=data.item_type,
        description=data.description,
        quantity=data.quantity,
        unit=data.unit,
        rate=data.rate,
        amount=data.amount,
        project_id=data.project_id,
        tax_applicable=data.tax_applicable,
        sort_order=max_order + 1,
    )
    _recalculate_invoice_totals(invoice)
    return item


def _recalculate_invoice_totals(invoice: Invoice) -> None:
    """Recalculate invoice subtotal and total."""
    items = LineItem.objects.filter(invoice=invoice)
    subtotal = Decimal("0")
    for item in items:
        subtotal += Decimal(str(item.amount))
    invoice.subtotal = subtotal
    invoice.total = subtotal + invoice.tax_amount
    invoice.amount_due = invoice.total - invoice.amount_paid
    invoice.save(update_fields=["subtotal", "total", "amount_due", "updated_at"])
