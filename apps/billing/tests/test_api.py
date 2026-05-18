"""API tests for Billing endpoints.

Tests time, invoices, payments under ``/api/v1/billing/``.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.billing.models.time_entry import TimeEntry
from apps.billing.models.invoice import Invoice
from apps.billing.models.payment import Payment

client = Client()


@pytest.fixture
def time_entry(tenant_id: str) -> TimeEntry:
    """Create a test time entry."""
    return TimeEntry.objects.create(
        tenant_id=tenant_id,
        user_id="user-001",
        description="Work on campaign",
        hours=4.5,
        rate=100.00,
        date="2024-06-15",
        billable=True,
    )


@pytest.fixture
def invoice(tenant_id: str) -> Invoice:
    """Create a test invoice."""
    return Invoice.objects.create(
        tenant_id=tenant_id,
        invoice_number="INV-001",
        client_name="Test Client",
        amount=5000.00,
        currency="USD",
        status="draft",
        due_date="2024-07-15",
    )


@pytest.mark.django_db
def test_billing_health_requires_auth() -> None:
    """GET /billing/health without auth returns 401."""
    response = client.get("/api/v1/billing/health")
    assert response.status_code == 401


@pytest.mark.django_db
def test_billing_health(auth_headers: dict[str, str]) -> None:
    """GET /billing/health returns module health."""
    response = client.get("/api/v1/billing/health", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["module"] == "billing"


@pytest.mark.django_db
def test_list_time_entries(auth_headers: dict[str, str], time_entry: TimeEntry) -> None:
    """GET /billing/time-entries returns time entries."""
    response = client.get("/api/v1/billing/time-entries", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_time_entry(auth_headers: dict[str, str]) -> None:
    """POST /billing/time-entries creates a time entry."""
    payload = {
        "user_id": "user-002",
        "description": "Design work",
        "hours": 3.0,
        "rate": 125.00,
        "date": "2024-06-16",
        "billable": True,
    }
    response = client.post(
        "/api/v1/billing/time-entries",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Design work"


@pytest.mark.django_db
def test_list_invoices(auth_headers: dict[str, str], invoice: Invoice) -> None:
    """GET /billing/invoices returns invoices."""
    response = client.get("/api/v1/billing/invoices", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_invoice(auth_headers: dict[str, str]) -> None:
    """POST /billing/invoices creates an invoice."""
    payload = {
        "invoice_number": "INV-002",
        "client_name": "API Client",
        "amount": 3000.00,
        "currency": "EUR",
        "status": "draft",
        "due_date": "2024-08-01",
    }
    response = client.post(
        "/api/v1/billing/invoices",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["invoice_number"] == "INV-002"


@pytest.mark.django_db
def test_list_payments(auth_headers: dict[str, str]) -> None:
    """GET /billing/payments returns payments."""
    response = client.get("/api/v1/billing/payments", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
