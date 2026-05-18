"""API tests for Campaign endpoints.

Tests CRUD, lifecycle, budget under ``/api/v1/campaigns/``.
"""

from __future__ import annotations

from datetime import date

import pytest
from django.test import Client

from apps.campaigns.models import Campaign, CampaignChannel

client = Client()


@pytest.fixture
def campaign(tenant_id: str) -> Campaign:
    """Create a test campaign."""
    return Campaign.objects.create(
        tenant_id=tenant_id,
        name="Test Campaign",
        description="A campaign for API testing",
        objective="awareness",
        stage=Campaign.Stage.PLANNING,
        status=Campaign.Status.DRAFT,
        budget=10000.00,
        currency="USD",
        pacing_type=Campaign.PacingType.EVEN,
        channels=["social", "email"],
    )


@pytest.mark.django_db
def test_campaigns_health_requires_auth() -> None:
    """GET /campaigns/health without auth returns 401."""
    response = client.get("/api/v1/campaigns/health")
    assert response.status_code == 401


@pytest.mark.django_db
def test_campaigns_health(auth_headers: dict[str, str]) -> None:
    """GET /campaigns/health returns module health."""
    response = client.get("/api/v1/campaigns/health", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["module"] == "campaigns"


@pytest.mark.django_db
def test_list_campaigns(auth_headers: dict[str, str], campaign: Campaign) -> None:
    """GET /campaigns/ returns a list of campaigns."""
    response = client.get("/api/v1/campaigns/", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_list_campaigns_filtered(auth_headers: dict[str, str], campaign: Campaign) -> None:
    """GET /campaigns/?status=draft filters by status."""
    response = client.get("/api/v1/campaigns/?status=draft", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert all(c["status"] == "draft" for c in data)


@pytest.mark.django_db
def test_create_campaign(auth_headers: dict[str, str]) -> None:
    """POST /campaigns/ creates a campaign."""
    payload = {
        "name": "API Test Campaign",
        "description": "Created via API",
        "objective": "conversions",
        "start_date": str(date.today()),
        "end_date": str(date.today()),
        "budget": 5000.00,
        "currency": "EUR",
        "pacing_type": "even",
        "attribution_model": "last_touch",
        "channels": ["social", "search"],
        "target_audience": {"age": "25-34"},
        "kpis": {"roas": 3.0},
    }
    response = client.post(
        "/api/v1/campaigns/",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "API Test Campaign"
    assert "id" in data


@pytest.mark.django_db
def test_get_campaign(auth_headers: dict[str, str], campaign: Campaign) -> None:
    """GET /campaigns/{campaign_id} returns a campaign."""
    response = client.get(f"/api/v1/campaigns/{campaign.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Campaign"


@pytest.mark.django_db
def test_update_campaign(auth_headers: dict[str, str], campaign: Campaign) -> None:
    """PUT /campaigns/{campaign_id} updates a campaign."""
    payload = {"name": "Updated Campaign", "description": "Updated via API"}
    response = client.put(
        f"/api/v1/campaigns/{campaign.id}",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Campaign"


@pytest.mark.django_db
def test_delete_campaign(auth_headers: dict[str, str], campaign: Campaign) -> None:
    """DELETE /campaigns/{campaign_id} removes a campaign."""
    response = client.delete(f"/api/v1/campaigns/{campaign.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    assert not Campaign.objects.filter(id=campaign.id).exists()


@pytest.mark.django_db
def test_clone_campaign(auth_headers: dict[str, str], campaign: Campaign) -> None:
    """POST /campaigns/{campaign_id}/clone clones a campaign."""
    response = client.post(
        f"/api/v1/campaigns/{campaign.id}/clone?new_name=Cloned%20Campaign",
        {},
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Cloned Campaign"
    assert Campaign.objects.filter(name="Cloned Campaign").exists()


@pytest.mark.django_db
def test_list_channels(auth_headers: dict[str, str], campaign: Campaign) -> None:
    """GET /campaigns/{campaign_id}/channels returns channels."""
    CampaignChannel.objects.create(
        campaign=campaign,
        channel_type="social",
        platform="twitter",
        config={},
    )
    response = client.get(f"/api/v1/campaigns/{campaign.id}/channels", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_channel(auth_headers: dict[str, str], campaign: Campaign) -> None:
    """POST /campaigns/{campaign_id}/channels adds a channel."""
    payload = {
        "channel_type": "email",
        "platform": "mailchimp",
        "config": {"list_id": "abc123"},
        "daily_budget": 100.00,
    }
    response = client.post(
        f"/api/v1/campaigns/{campaign.id}/channels",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["channel_type"] == "email"


@pytest.mark.django_db
def test_campaign_lifecycle_stages(auth_headers: dict[str, str], campaign: Campaign) -> None:
    """GET /campaigns/lifecycle/{campaign_id}/stages returns available stages."""
    response = client.get(f"/api/v1/campaigns/lifecycle/{campaign.id}/stages", **auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.django_db
def test_campaign_transition(auth_headers: dict[str, str], campaign: Campaign) -> None:
    """POST /campaigns/lifecycle/{campaign_id}/transition changes stage."""
    payload = {"target_stage": "launch"}
    response = client.post(
        f"/api/v1/campaigns/lifecycle/{campaign.id}/transition",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "success" in data


@pytest.mark.django_db
def test_budget_pacing(auth_headers: dict[str, str], campaign: Campaign) -> None:
    """GET /campaigns/budget/{campaign_id}/pacing returns pacing data."""
    response = client.get(f"/api/v1/campaigns/budget/{campaign.id}/pacing", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "pacing" in data or "budget" in str(data).lower()


@pytest.mark.django_db
def test_budget_alerts(auth_headers: dict[str, str], campaign: Campaign) -> None:
    """GET /campaigns/budget/{campaign_id}/alerts returns budget alerts."""
    response = client.get(f"/api/v1/campaigns/budget/{campaign.id}/alerts", **auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.django_db
def test_budget_spend(auth_headers: dict[str, str], campaign: Campaign) -> None:
    """POST /campaigns/budget/{campaign_id}/spend records spend."""
    payload = {"amount": 150.00, "channel": "social", "description": "Test spend"}
    response = client.post(
        f"/api/v1/campaigns/budget/{campaign.id}/spend",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
