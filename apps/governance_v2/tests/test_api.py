"""API tests for Governance v2 endpoints.

Tests scan, rules, approvals, GDPR under ``/api/v1/governance/``.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.governance_v2.models.compliance import ComplianceRule
from apps.governance_v2.models.gdpr import GDPRConsent, DSRRequest
from apps.governance_v2.models.approval import ApprovalRequest

client = Client()


@pytest.fixture
def compliance_rule(tenant_id: str) -> ComplianceRule:
    """Create a test compliance rule."""
    return ComplianceRule.objects.create(
        tenant_id=tenant_id,
        name="Test Rule",
        description="A compliance rule for API testing",
        rule_type="content",
        config={"keywords": ["prohibited"]},
        is_active=True,
    )


@pytest.fixture
def gdpr_consent(tenant_id: str) -> GDPRConsent:
    """Create a test GDPR consent record."""
    return GDPRConsent.objects.create(
        tenant_id=tenant_id,
        user_id="user-001",
        consent_type="marketing",
        granted=True,
        ip_address="192.168.1.1",
    )


@pytest.fixture
def approval_request(tenant_id: str) -> ApprovalRequest:
    """Create a test approval request."""
    return ApprovalRequest.objects.create(
        tenant_id=tenant_id,
        requester_id="user-001",
        approver_id="user-002",
        title="Budget Approval",
        description="Approve Q3 budget",
        status="pending",
    )


@pytest.mark.django_db
def test_governance_health_requires_auth() -> None:
    """GET /governance/health without auth returns 401."""
    response = client.get("/api/v1/governance/health")
    assert response.status_code == 401


@pytest.mark.django_db
def test_governance_health(auth_headers: dict[str, str]) -> None:
    """GET /governance/health returns module health."""
    response = client.get("/api/v1/governance/health", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["module"] == "governance_v2"


@pytest.mark.django_db
def test_list_compliance_rules(auth_headers: dict[str, str], compliance_rule: ComplianceRule) -> None:
    """GET /governance/rules returns compliance rules."""
    response = client.get("/api/v1/governance/rules", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


@pytest.mark.django_db
def test_create_compliance_rule(auth_headers: dict[str, str]) -> None:
    """POST /governance/rules creates a compliance rule."""
    payload = {
        "name": "API Rule",
        "description": "Created via API",
        "rule_type": "brand_safety",
        "config": {"threshold": 0.8},
        "is_active": True,
    }
    response = client.post(
        "/api/v1/governance/rules",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "API Rule"


@pytest.mark.django_db
def test_update_compliance_rule(auth_headers: dict[str, str], compliance_rule: ComplianceRule) -> None:
    """PUT /governance/rules/{id} updates a rule."""
    payload = {"name": "Updated Rule", "description": "Updated", "config": {}}
    response = client.put(
        f"/api/v1/governance/rules/{compliance_rule.id}",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Rule"


@pytest.mark.django_db
def test_check_compliance(auth_headers: dict[str, str]) -> None:
    """POST /governance/rules/check runs compliance check."""
    payload = {"text": "This is a test content piece.", "content_type": "social_post"}
    response = client.post(
        "/api/v1/governance/rules/check",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "passed" in data or "violations" in data


@pytest.mark.django_db
def test_scan_content(auth_headers: dict[str, str]) -> None:
    """POST /governance/scan scans content for compliance."""
    payload = {"content": "Test content for scanning", "content_type": "text"}
    response = client.post(
        "/api/v1/governance/scan",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "violations" in data or "issues" in data or "passed" in data


@pytest.mark.django_db
def test_record_consent(auth_headers: dict[str, str]) -> None:
    """POST /governance/gdpr/consent records a consent."""
    payload = {
        "user_id": "user-api-001",
        "tenant_id": "test-tenant-001",
        "consent_type": "analytics",
        "granted": True,
        "ip_address": "10.0.0.1",
    }
    response = client.post(
        "/api/v1/governance/gdpr/consent",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["granted"] is True


@pytest.mark.django_db
def test_list_approvals(auth_headers: dict[str, str], approval_request: ApprovalRequest) -> None:
    """GET /governance/approvals returns approval requests."""
    response = client.get("/api/v1/governance/approvals", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


@pytest.mark.django_db
def test_create_approval(auth_headers: dict[str, str]) -> None:
    """POST /governance/approvals creates an approval request."""
    payload = {
        "title": "API Approval",
        "description": "Created via API",
        "requester_id": "user-001",
        "approver_id": "user-002",
        "status": "pending",
    }
    response = client.post(
        "/api/v1/governance/approvals",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "API Approval"


@pytest.mark.django_db
def test_approve_request(auth_headers: dict[str, str], approval_request: ApprovalRequest) -> None:
    """POST /governance/approvals/{id}/action approves a request."""
    payload = {"action": "approve", "comment": "Looks good"}
    response = client.post(
        f"/api/v1/governance/approvals/{approval_request.id}/action",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_list_dsr_requests(auth_headers: dict[str, str]) -> None:
    """GET /governance/gdpr/dsr returns DSR requests."""
    response = client.get("/api/v1/governance/gdpr/dsr", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.django_db
def test_submit_dsr(auth_headers: dict[str, str]) -> None:
    """POST /governance/gdpr/dsr submits a DSR request."""
    payload = {
        "user_id": "user-dsr-001",
        "tenant_id": "test-tenant-001",
        "request_type": "access",
        "description": "Request my data",
    }
    response = client.post(
        "/api/v1/governance/gdpr/dsr",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["request_type"] == "access"
