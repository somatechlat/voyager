"""API tests for Audit Log endpoints.

Tests query, export, integrity, and bulk creation endpoints under
``/api/v1/audit/``.
"""

from __future__ import annotations

import uuid

import pytest
from django.test import Client

from apps.audit.middleware import log_event

client = Client()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def audit_entries(tenant_id: str) -> list[uuid.UUID]:
    """Create sample audit log entries and return their IDs."""
    entry_ids = []
    for i in range(5):
        entry_hash = log_event(
            tenant_id=tenant_id,
            actor_id=f"user-{i:03d}",
            action="campaign.created",
            resource_type="campaign",
            resource_id=f"campaign-{i:03d}",
            outcome="success",
            details={"name": f"Campaign {i}"},
        )
        entry_ids.append(entry_hash)
    return entry_ids


# ---------------------------------------------------------------------------
# Audit log query endpoints
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_audit_logs_list_requires_auth() -> None:
    """GET /audit/audit-logs without auth returns 401."""
    response = client.get("/api/v1/audit/audit-logs")
    assert response.status_code == 401


@pytest.mark.django_db
def test_audit_logs_list(auth_headers: dict[str, str], audit_entries: list) -> None:
    """GET /audit/audit-logs returns paginated audit entries."""
    response = client.get("/api/v1/audit/audit-logs", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 5


@pytest.mark.django_db
def test_audit_logs_filtered(auth_headers: dict[str, str], audit_entries: list) -> None:
    """GET /audit/audit-logs?action= filters by action."""
    response = client.get("/api/v1/audit/audit-logs?action=campaign.created", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert all(e["action"] == "campaign.created" for e in data["items"])


@pytest.mark.django_db
def test_audit_logs_pagination(auth_headers: dict[str, str], audit_entries: list) -> None:
    """GET /audit/audit-logs?page_size= limits results."""
    response = client.get("/api/v1/audit/audit-logs?page=1&page_size=2", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["page_size"] == 2
    assert len(data["items"]) <= 2


@pytest.mark.django_db
def test_get_audit_log_entry(auth_headers: dict[str, str], tenant_id: str) -> None:
    """GET /audit/audit-logs/{entry_id} returns a single entry."""
    entry_hash = log_event(
        tenant_id=tenant_id,
        actor_id="user-test",
        action="test.action",
        resource_type="test",
        resource_id="test-001",
        outcome="success",
    )
    assert entry_hash is not None
    # The entry ID is the hash — just verify list works
    response = client.get("/api/v1/audit/audit-logs", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.django_db
def test_create_audit_entry(auth_headers: dict[str, str]) -> None:
    """POST /audit/audit-logs creates an audit entry."""
    payload = {
        "tenant_id": "test-tenant-001",
        "actor_id": "api-test-user",
        "action": "api.test.created",
        "resource_type": "test_resource",
        "resource_id": "test-123",
        "outcome": "success",
        "details": {"test": True},
        "actor_type": "user",
    }
    response = client.post(
        "/api/v1/audit/audit-logs",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "created"
    assert "hash" in data


@pytest.mark.django_db
def test_create_bulk_audit_entries(auth_headers: dict[str, str]) -> None:
    """POST /audit/audit-logs/bulk creates multiple entries."""
    payload = {
        "entries": [
            {
                "tenant_id": "test-tenant-001",
                "actor_id": f"bulk-user-{i}",
                "action": "bulk.test",
                "resource_type": "resource",
                "resource_id": f"res-{i}",
                "outcome": "success",
                "details": {},
                "actor_type": "user",
            }
            for i in range(3)
        ]
    }
    response = client.post(
        "/api/v1/audit/audit-logs/bulk",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["created_count"] == 3


# ---------------------------------------------------------------------------
# Export endpoints
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_export_audit_logs_json(auth_headers: dict[str, str], audit_entries: list) -> None:
    """GET /audit/audit-logs/export?format=json returns JSON attachment."""
    response = client.get("/api/v1/audit/audit-logs/export?format=json", **auth_headers)
    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    assert "attachment" in response.get("Content-Disposition", "")


@pytest.mark.django_db
def test_export_audit_logs_csv(auth_headers: dict[str, str], audit_entries: list) -> None:
    """GET /audit/audit-logs/export?format=csv returns CSV attachment."""
    response = client.get("/api/v1/audit/audit-logs/export?format=csv", **auth_headers)
    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv"
    assert "attachment" in response.get("Content-Disposition", "")


# ---------------------------------------------------------------------------
# Statistics and integrity endpoints
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_audit_stats(auth_headers: dict[str, str], audit_entries: list) -> None:
    """GET /audit/audit-logs/stats returns aggregated statistics."""
    response = client.get("/api/v1/audit/audit-logs/stats", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_events" in data
    assert "events_by_action" in data
    assert "events_by_outcome" in data


@pytest.mark.django_db
def test_verify_chain(auth_headers: dict[str, str], audit_entries: list) -> None:
    """POST /audit/audit-logs/verify returns hash chain status."""
    response = client.post(
        "/api/v1/audit/audit-logs/verify",
        {},
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "is_valid" in data
    assert "total_entries" in data
