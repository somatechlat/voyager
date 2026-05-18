"""API tests for Strategy endpoints.

Tests personas, competitors, strategies, OKR under ``/api/v1/strategy/``.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.strategy.models import Competitor, Persona, Strategy

client = Client()


@pytest.fixture
def persona(tenant_id: str) -> Persona:
    """Create a test persona."""
    return Persona.objects.create(
        tenant_id=tenant_id,
        name="Test Persona",
        description="A test persona",
        demographics={"age": "25-34", "gender": "all"},
        pain_points=["price"],
        goals=["efficiency"],
    )


@pytest.fixture
def competitor(tenant_id: str) -> Competitor:
    """Create a test competitor."""
    return Competitor.objects.create(
        tenant_id=tenant_id,
        name="Test Competitor",
        website="https://competitor.example.com",
        industry="tech",
        strengths=["brand"],
        weaknesses=["price"],
    )


@pytest.fixture
def strategy(tenant_id: str) -> Strategy:
    """Create a test strategy."""
    return Strategy.objects.create(
        tenant_id=tenant_id,
        name="Test Strategy",
        description="A strategy for API testing",
        objective="grow_market_share",
        status="active",
    )


@pytest.mark.django_db
def test_strategy_health_requires_auth() -> None:
    """GET /strategy/health without auth returns 401."""
    response = client.get("/api/v1/strategy/health")
    assert response.status_code == 401


@pytest.mark.django_db
def test_strategy_health(auth_headers: dict[str, str]) -> None:
    """GET /strategy/health returns module health."""
    response = client.get("/api/v1/strategy/health", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["module"] == "strategy"


@pytest.mark.django_db
def test_list_personas(auth_headers: dict[str, str], persona: Persona) -> None:
    """GET /strategy/personas returns personas."""
    response = client.get("/api/v1/strategy/personas", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_persona(auth_headers: dict[str, str]) -> None:
    """POST /strategy/personas creates a persona."""
    payload = {
        "name": "API Persona",
        "description": "Created via API",
        "demographics": {"age": "18-24"},
        "pain_points": ["cost"],
        "goals": ["speed"],
    }
    response = client.post(
        "/api/v1/strategy/personas",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "API Persona"


@pytest.mark.django_db
def test_get_persona(auth_headers: dict[str, str], persona: Persona) -> None:
    """GET /strategy/personas/{id} returns a persona."""
    response = client.get(f"/api/v1/strategy/personas/{persona.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Persona"


@pytest.mark.django_db
def test_update_persona(auth_headers: dict[str, str], persona: Persona) -> None:
    """PUT /strategy/personas/{id} updates a persona."""
    payload = {"name": "Updated Persona", "description": "Updated", "demographics": {}}
    response = client.put(
        f"/api/v1/strategy/personas/{persona.id}",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Persona"


@pytest.mark.django_db
def test_delete_persona(auth_headers: dict[str, str], persona: Persona) -> None:
    """DELETE /strategy/personas/{id} removes a persona."""
    response = client.delete(f"/api/v1/strategy/personas/{persona.id}", **auth_headers)
    assert response.status_code == 200
    assert not Persona.objects.filter(id=persona.id).exists()


@pytest.mark.django_db
def test_list_competitors(auth_headers: dict[str, str], competitor: Competitor) -> None:
    """GET /strategy/competitors returns competitors."""
    response = client.get("/api/v1/strategy/competitors", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_competitor(auth_headers: dict[str, str]) -> None:
    """POST /strategy/competitors creates a competitor."""
    payload = {
        "name": "API Competitor",
        "website": "https://api.example.com",
        "industry": "saas",
        "strengths": ["ux"],
        "weaknesses": ["support"],
    }
    response = client.post(
        "/api/v1/strategy/competitors",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "API Competitor"


@pytest.mark.django_db
def test_get_competitor(auth_headers: dict[str, str], competitor: Competitor) -> None:
    """GET /strategy/competitors/{id} returns a competitor."""
    response = client.get(f"/api/v1/strategy/competitors/{competitor.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Competitor"


@pytest.mark.django_db
def test_list_strategies(auth_headers: dict[str, str], strategy: Strategy) -> None:
    """GET /strategy/strategies returns strategies."""
    response = client.get("/api/v1/strategy/strategies", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_strategy(auth_headers: dict[str, str]) -> None:
    """POST /strategy/strategies creates a strategy."""
    payload = {
        "name": "API Strategy",
        "description": "Created via API",
        "objective": "brand_awareness",
        "status": "draft",
    }
    response = client.post(
        "/api/v1/strategy/strategies",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "API Strategy"


@pytest.mark.django_db
def test_get_strategy(auth_headers: dict[str, str], strategy: Strategy) -> None:
    """GET /strategy/strategies/{id} returns a strategy."""
    response = client.get(f"/api/v1/strategy/strategies/{strategy.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Strategy"
