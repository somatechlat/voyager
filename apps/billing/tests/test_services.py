"""Tests for billing services — time tracking, invoicing, payments."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.billing.models import Invoice, Payment, TimeEntry
from apps.billing.services import invoicing as invoice_service
from apps.billing.services import payments as payment_service
from apps.billing.services import time_tracking as time_service


@pytest.fixture
def tenant_id() -> str:
    return "test-tenant-billing"


@pytest.fixture
def create_client_for_billing(tenant_id, db):
    from apps.clients.models import Client

    def _create(**kwargs):
        defaults = {
            "tenant_id": tenant_id,
            "name": f"Billing Client {uuid.uuid4().hex[:8]}",
            "slug": f"billing-{uuid.uuid4().hex[:8]}",
        }
        defaults.update(kwargs)
        return Client.objects.create(**defaults)

    return _create


@pytest.fixture
def create_time_entry(tenant_id, create_client_for_billing, db):
    def _create(**kwargs):
        client = kwargs.pop("client", None) or create_client_for_billing()
        project = kwargs.pop("project", None)
        defaults = {
            "tenant_id": tenant_id,
            "user_id": f"user-{uuid.uuid4().hex[:6]}",
            "client": client,
            "task_name": "Test Task",
            "description": "Test description",
            "tracking_mode": TimeEntry.TrackingMode.MANUAL,
            "started_at": timezone.now(),
            "ended_at": timezone.now() + timedelta(hours=2),
            "duration_minutes": 120,
            "rounded_minutes": 120,
            "billing_rate": Decimal("100.00"),
            "billable_amount": Decimal("200.00"),
            "is_billable": True,
            "status": TimeEntry.Status.SUBMITTED,
        }
        defaults.update(kwargs)
        if project:
            defaults["project"] = project
        return TimeEntry.objects.create(**defaults)

    return _create


@pytest.fixture
def create_invoice(tenant_id, create_client_for_billing, db):
    def _create(**kwargs):
        client = kwargs.pop("client", None) or create_client_for_billing()
        defaults = {
            "tenant_id": tenant_id,
            "client": client,
            "invoice_number": f"INV-{uuid.uuid4().hex[:8].upper()}",
            "status": Invoice.Status.DRAFT,
            "subtotal": Decimal("1000.00"),
            "tax_amount": Decimal("100.00"),
            "total": Decimal("1100.00"),
            "amount_paid": Decimal("0.00"),
            "amount_due": Decimal("1100.00"),
            "currency": "USD",
            "invoice_date": date.today(),
            "due_date": date.today() + timedelta(days=30),
            "payment_terms": Invoice.PaymentTerms.NET_30,
        }
        defaults.update(kwargs)
        return Invoice.objects.create(**defaults)

    return _create


@pytest.fixture
def create_payment(tenant_id, create_client_for_billing, db):
    def _create(invoice=None, **kwargs):
        client = kwargs.pop("client", None) or create_client_for_billing()
        defaults = {
            "tenant_id": tenant_id,
            "invoice": invoice,
            "client": client,
            "amount": Decimal("500.00"),
            "currency": "USD",
            "status": Payment.Status.SUCCEEDED,
            "payment_method_type": Payment.PaymentMethodType.CARD,
            "stripe_payment_intent_id": f"pi_{uuid.uuid4().hex[:12]}",
        }
        defaults.update(kwargs)
        return Payment.objects.create(**defaults)

    return _create


# ── Time Tracking Service Tests ───────────────────────────────────


class TestTimeTrackingService:
    def test_create_time_entry(self, tenant_id, create_client_for_billing):
        client = create_client_for_billing()
        entry = time_service.create_time_entry(
            tenant_id=tenant_id,
            user_id="user-1",
            client_id=client.id,
            task_name="Design Work",
            description="Homepage design",
            duration_minutes=120,
            billing_rate=Decimal("150.00"),
            started_at=timezone.now(),
            ended_at=timezone.now() + timedelta(hours=2),
        )
        assert entry is not None
        assert entry.task_name == "Design Work"
        assert TimeEntry.objects.filter(id=entry.id).exists()

    def test_create_time_entry_rounding(self, tenant_id, create_client_for_billing):
        client = create_client_for_billing()
        entry = time_service.create_time_entry(
            tenant_id=tenant_id,
            user_id="user-2",
            client_id=client.id,
            task_name="Dev Work",
            duration_minutes=65,
            billing_rate=Decimal("100.00"),
        )
        assert entry.rounded_minutes == 60

    def test_get_time_entry(self, create_time_entry):
        e = create_time_entry(task_name="Specific Task")
        result = time_service.get_time_entry(e.id)
        assert result is not None
        assert result.task_name == "Specific Task"

    def test_get_time_entry_not_found(self):
        result = time_service.get_time_entry(99999)
        assert result is None

    def test_list_time_entries(self, create_time_entry):
        create_time_entry(task_name="Task 1")
        create_time_entry(task_name="Task 2")
        result = time_service.list_time_entries("test-tenant-billing")
        assert result["total"] >= 2

    def test_update_time_entry(self, create_time_entry):
        e = create_time_entry(task_name="Old Task")
        updated = time_service.update_time_entry(e.id, {"task_name": "New Task"})
        assert updated.task_name == "New Task"

    def test_delete_time_entry(self, create_time_entry):
        e = create_time_entry()
        time_service.delete_time_entry(e.id)
        assert not TimeEntry.objects.filter(id=e.id).exists()

    def test_list_time_entries_by_status(self, create_time_entry):
        create_time_entry(status=TimeEntry.Status.SUBMITTED)
        create_time_entry(status=TimeEntry.Status.APPROVED)
        result = time_service.list_time_entries(
            "test-tenant-billing", status=TimeEntry.Status.SUBMITTED
        )
        assert all(e.status == TimeEntry.Status.SUBMITTED for e in result["results"])

    def test_create_time_entry_invalid_status(self, tenant_id, create_client_for_billing):
        client = create_client_for_billing()
        with pytest.raises(ValueError):
            time_service.create_time_entry(
                tenant_id=tenant_id,
                user_id="user-3",
                client_id=client.id,
                task_name="Fail Task",
                duration_minutes=-10,
            )


# ── Invoicing Service Tests ───────────────────────────────────────


class TestInvoicingService:
    def test_create_invoice(self, tenant_id, create_client_for_billing):
        client = create_client_for_billing()
        inv = invoice_service.create_invoice(
            tenant_id=tenant_id,
            client_id=client.id,
            invoice_number="INV-001",
            subtotal=Decimal("2000.00"),
            tax_amount=Decimal("200.00"),
            total=Decimal("2200.00"),
        )
        assert inv is not None
        assert inv.invoice_number == "INV-001"
        assert Invoice.objects.filter(id=inv.id).exists()

    def test_get_invoice(self, create_invoice):
        inv = create_invoice(invoice_number="INV-GET")
        result = invoice_service.get_invoice(inv.id)
        assert result is not None
        assert result.invoice_number == "INV-GET"

    def test_get_invoice_not_found(self):
        result = invoice_service.get_invoice(99999)
        assert result is None

    def test_list_invoices(self, create_invoice):
        create_invoice(invoice_number="INV-A")
        create_invoice(invoice_number="INV-B")
        result = invoice_service.list_invoices("test-tenant-billing")
        assert result["total"] >= 2

    def test_list_invoices_status_filter(self, create_invoice):
        create_invoice(invoice_number="INV-DRAFT", status=Invoice.Status.DRAFT)
        create_invoice(invoice_number="INV-SENT", status=Invoice.Status.SENT)
        result = invoice_service.list_invoices("test-tenant-billing", status=Invoice.Status.DRAFT)
        assert all(inv.status == Invoice.Status.DRAFT for inv in result["results"])

    def test_update_invoice(self, create_invoice):
        inv = create_invoice()
        updated = invoice_service.update_invoice(
            inv.id, {"status": Invoice.Status.SENT, "notes": "Updated notes"}
        )
        assert updated.status == Invoice.Status.SENT
        assert updated.notes == "Updated notes"

    def test_mark_invoice_paid(self, create_invoice):
        inv = create_invoice(status=Invoice.Status.SENT, amount_paid=Decimal("0.00"), paid_at=None)
        updated = invoice_service.mark_invoice_paid(
            inv.id, amount=Decimal("1100.00"), method="card"
        )
        assert updated.status == Invoice.Status.PAID
        assert updated.amount_paid == Decimal("1100.00")

    def test_void_invoice(self, create_invoice):
        inv = create_invoice(status=Invoice.Status.SENT)
        updated = invoice_service.void_invoice(inv.id)
        assert updated.status == Invoice.Status.VOID

    def test_list_invoices_empty_tenant(self, tenant_id):
        result = invoice_service.list_invoices(tenant_id + "-none")
        assert result["total"] == 0
        assert result["results"] == []


# ── Payment Service Tests ─────────────────────────────────────────


class TestPaymentService:
    def test_create_payment(self, tenant_id, create_invoice):
        inv = create_invoice()
        payment = payment_service.create_payment(
            tenant_id=tenant_id,
            invoice_id=inv.id,
            amount=Decimal("500.00"),
            currency="USD",
            payment_method_type=Payment.PaymentMethodType.CARD,
        )
        assert payment is not None
        assert payment.amount == Decimal("500.00")
        assert Payment.objects.filter(id=payment.id).exists()

    def test_get_payment(self, create_payment):
        p = create_payment(amount=Decimal("250.00"))
        result = payment_service.get_payment(p.id)
        assert result is not None
        assert result.amount == Decimal("250.00")

    def test_get_payment_not_found(self):
        result = payment_service.get_payment(99999)
        assert result is None

    def test_list_payments(self, create_payment):
        create_payment(amount=Decimal("100.00"))
        create_payment(amount=Decimal("200.00"))
        result = payment_service.list_payments("test-tenant-billing")
        assert result["total"] >= 2

    def test_refund_payment(self, create_payment):
        p = create_payment(
            amount=Decimal("1000.00"),
            status=Payment.Status.SUCCEEDED,
            refund_amount=Decimal("0.00"),
        )
        refunded = payment_service.refund_payment(
            p.id, amount=Decimal("250.00"), reason="Customer request"
        )
        assert refunded.refund_amount == Decimal("250.00")

    def test_list_payments_status_filter(self, create_payment):
        create_payment(status=Payment.Status.SUCCEEDED)
        create_payment(status=Payment.Status.FAILED)
        result = payment_service.list_payments(
            "test-tenant-billing", status=Payment.Status.SUCCEEDED
        )
        assert all(p.status == Payment.Status.SUCCEEDED for p in result["results"])

    def test_create_payment_zero_amount(self, tenant_id, create_invoice):
        inv = create_invoice()
        with pytest.raises(ValueError):
            payment_service.create_payment(
                tenant_id=tenant_id,
                invoice_id=inv.id,
                amount=Decimal("0.00"),
            )
