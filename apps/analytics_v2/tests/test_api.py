"""API tests for Analytics v2 endpoints.

Tests dashboards, reports, export under ``/api/v1/analytics/``.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.analytics_v2.models.dashboard import Dashboard
from apps.analytics_v2.models.report import ReportTemplate

client = Client()


@pytest.fixture
def dashboard(tenant_id: str) -> Dashboard:
    """Create a test dashboard."""
    return Dashboard.objects.create(
        tenant_id=tenant_id,
        name="Test Dashboard",
        description="Dashboard for API tests",
        layout={"widgets": []},
        is_public=False,
    )


@pytest.fixture
def report_template(tenant_id: str) -> ReportTemplate:
    """Create a test report template."""
    return ReportTemplate.objects.create(
        tenant_id=tenant_id,
        name="Test Report",
        description="Report for API tests",
        report_type="performance",
        config={"metrics": ["impressions", "clicks"]},
    )


@pytest.mark.django_db
def test_analytics_health_requires_auth() -> None:
    """GET /analytics/health without auth returns 401."""
    response = client.get("/api/v1/analytics/health")
    assert response.status_code == 401


@pytest.mark.django_db
def test_analytics_health(auth_headers: dict[str, str]) -> None:
    """GET /analytics/health returns module health."""
    response = client.get("/api/v1/analytics/health", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["module"] == "analytics_v2"


@pytest.mark.django_db
def test_list_dashboards(auth_headers: dict[str, str], dashboard: Dashboard) -> None:
    """GET /analytics/dashboards returns dashboards."""
    response = client.get("/api/v1/analytics/dashboards", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_dashboard(auth_headers: dict[str, str]) -> None:
    """POST /analytics/dashboards creates a dashboard."""
    payload = {
        "name": "API Dashboard",
        "description": "Created via API",
        "layout": {"widgets": [{"type": "chart", "x": 0, "y": 0}]},
        "is_public": False,
    }
    response = client.post(
        "/api/v1/analytics/dashboards",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "API Dashboard"


@pytest.mark.django_db
def test_get_dashboard(auth_headers: dict[str, str], dashboard: Dashboard) -> None:
    """GET /analytics/dashboards/{id} returns a dashboard."""
    response = client.get(f"/api/v1/analytics/dashboards/{dashboard.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Dashboard"


@pytest.mark.django_db
def test_list_reports(auth_headers: dict[str, str], report_template: ReportTemplate) -> None:
    """GET /analytics/reports returns report templates."""
    response = client.get("/api/v1/analytics/reports", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_report(auth_headers: dict[str, str]) -> None:
    """POST /analytics/reports creates a report template."""
    payload = {
        "name": "API Report",
        "description": "Created via API",
        "report_type": "summary",
        "config": {"metrics": ["roas"]},
    }
    response = client.post(
        "/api/v1/analytics/reports",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "API Report"
