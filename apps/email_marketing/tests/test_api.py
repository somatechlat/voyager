"""API tests for Email Marketing endpoints.

Tests templates, campaigns, segments under ``/api/v1/email/``.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.email_marketing.models.template import EmailTemplate
from apps.email_marketing.models.campaign import EmailCampaign
from apps.email_marketing.models.segment import AudienceSegment

client = Client()


@pytest.fixture
def email_template(tenant_id: str) -> EmailTemplate:
    """Create a test email template."""
    return EmailTemplate.objects.create(
        tenant_id=tenant_id,
        name="Test Template",
        subject="Hello {{ name }}!",
        body_html="<p>Welcome {{ name }}!</p>",
        body_text="Welcome {{ name }}!",
        category="welcome",
    )


@pytest.fixture
def email_campaign(tenant_id: str) -> EmailCampaign:
    """Create a test email campaign."""
    return EmailCampaign.objects.create(
        tenant_id=tenant_id,
        name="Test Campaign",
        subject="Summer Sale",
        status="draft",
        campaign_type="promotional",
    )


@pytest.fixture
def audience_segment(tenant_id: str) -> AudienceSegment:
    """Create a test audience segment."""
    return AudienceSegment.objects.create(
        tenant_id=tenant_id,
        name="Test Segment",
        description="Active subscribers",
        criteria={"status": "active"},
        subscriber_count=500,
    )


@pytest.mark.django_db
def test_email_health_requires_auth() -> None:
    """GET /email/health without auth returns 401."""
    response = client.get("/api/v1/email/health")
    assert response.status_code == 401


@pytest.mark.django_db
def test_email_health(auth_headers: dict[str, str]) -> None:
    """GET /email/health returns module health."""
    response = client.get("/api/v1/email/health", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["module"] == "email_marketing"


@pytest.mark.django_db
def test_list_email_templates(auth_headers: dict[str, str], email_template: EmailTemplate) -> None:
    """GET /email/templates returns templates."""
    response = client.get("/api/v1/email/templates", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_email_template(auth_headers: dict[str, str]) -> None:
    """POST /email/templates creates a template."""
    payload = {
        "name": "API Template",
        "subject": "New {{ topic }}",
        "body_html": "<p>Hello!</p>",
        "body_text": "Hello!",
        "category": "newsletter",
    }
    response = client.post(
        "/api/v1/email/templates",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "API Template"


@pytest.mark.django_db
def test_list_email_campaigns(auth_headers: dict[str, str], email_campaign: EmailCampaign) -> None:
    """GET /email/campaigns returns campaigns."""
    response = client.get("/api/v1/email/campaigns", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_email_campaign(auth_headers: dict[str, str]) -> None:
    """POST /email/campaigns creates a campaign."""
    payload = {
        "name": "API Campaign",
        "subject": "API Test Subject",
        "status": "draft",
        "campaign_type": "newsletter",
    }
    response = client.post(
        "/api/v1/email/campaigns",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "API Campaign"


@pytest.mark.django_db
def test_list_segments(auth_headers: dict[str, str], audience_segment: AudienceSegment) -> None:
    """GET /email/segments returns audience segments."""
    response = client.get("/api/v1/email/segments", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_segment(auth_headers: dict[str, str]) -> None:
    """POST /email/segments creates a segment."""
    payload = {
        "name": "API Segment",
        "description": "Created via API",
        "criteria": {"engaged": True},
        "subscriber_count": 0,
    }
    response = client.post(
        "/api/v1/email/segments",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "API Segment"
