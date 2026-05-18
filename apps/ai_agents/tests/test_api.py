"""API tests for AI Agents endpoints.

Tests agents, memory, context under ``/api/v1/agents/``.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.ai_agents.models.agent import Agent

client = Client()


@pytest.fixture
def agent(tenant_id: str) -> Agent:
    """Create a test agent."""
    return Agent.objects.create(
        tenant_id=tenant_id,
        name="Test Agent",
        description="An agent for API testing",
        agent_type="marketing",
        config={"model": "gpt-4", "temperature": 0.7},
        status="active",
    )


@pytest.mark.django_db
def test_agents_health_requires_auth() -> None:
    """GET /agents/health without auth returns 401."""
    response = client.get("/api/v1/agents/health")
    assert response.status_code == 401


@pytest.mark.django_db
def test_agents_health(auth_headers: dict[str, str]) -> None:
    """GET /agents/health returns module health."""
    response = client.get("/api/v1/agents/health", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.django_db
def test_list_agents(auth_headers: dict[str, str], agent: Agent) -> None:
    """GET /agents/agents returns agents."""
    response = client.get("/api/v1/agents/agents", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "agents" in data
    assert data["total"] >= 1


@pytest.mark.django_db
def test_create_agent(auth_headers: dict[str, str]) -> None:
    """POST /agents/agents creates an agent."""
    payload = {
        "name": "API Agent",
        "description": "Created via API",
        "agent_type": "analytics",
        "config": {"model": "gpt-4"},
        "status": "draft",
    }
    response = client.post(
        "/api/v1/agents/agents",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "API Agent"


@pytest.mark.django_db
def test_get_agent(auth_headers: dict[str, str], agent: Agent) -> None:
    """GET /agents/agents/{agent_id} returns an agent."""
    response = client.get(f"/api/v1/agents/agents/{agent.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Agent"


@pytest.mark.django_db
def test_update_agent(auth_headers: dict[str, str], agent: Agent) -> None:
    """PUT /agents/agents/{agent_id} updates an agent."""
    payload = {"name": "Updated Agent", "config": {"model": "gpt-4"}}
    response = client.put(
        f"/api/v1/agents/agents/{agent.id}",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Agent"


@pytest.mark.django_db
def test_delete_agent(auth_headers: dict[str, str], agent: Agent) -> None:
    """DELETE /agents/agents/{agent_id} removes an agent."""
    response = client.delete(f"/api/v1/agents/agents/{agent.id}", **auth_headers)
    assert response.status_code == 200
    assert not Agent.objects.filter(id=agent.id).exists()


@pytest.mark.django_db
def test_run_agent(auth_headers: dict[str, str], agent: Agent) -> None:
    """POST /agents/agents/{agent_id}/run triggers agent execution."""
    payload = {"input": "Analyze our Q3 campaign performance"}
    response = client.post(
        f"/api/v1/agents/agents/{agent.id}/run",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
