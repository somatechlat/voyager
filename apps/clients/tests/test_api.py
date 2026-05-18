"""API tests for Clients endpoints.

Tests clients, projects, communications under ``/api/v1/clients/``.
"""

from __future__ import annotations

import pytest
from django.test import Client as DjangoClient

from apps.clients.models.client import Client, ClientContact
from apps.clients.models.project import Project
from apps.clients.models.communication import CommunicationLog

client = DjangoClient()


@pytest.fixture
def test_client(tenant_id: str):
    """Create a test client."""
    return Client.objects.create(
        tenant_id=tenant_id,
        name="Test Client",
        slug="test-client",
        industry="tech",
        status="active",
        tier="premium",
        contact_name="Jane Doe",
        contact_email="jane@example.com",
    )


@pytest.fixture
def project(test_client) -> Project:
    """Create a test project."""
    return Project.objects.create(
        client=test_client,
        name="Test Project",
        description="A project for API testing",
        status="active",
        budget=25000.00,
    )


@pytest.mark.django_db
def test_clients_health_requires_auth() -> None:
    """GET /clients/health without auth returns 401."""
    response = client.get("/api/v1/clients/health")
    assert response.status_code == 401


@pytest.mark.django_db
def test_clients_health(auth_headers: dict[str, str]) -> None:
    """GET /clients/health returns module health."""
    response = client.get("/api/v1/clients/health", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["module"] == "clients"


@pytest.mark.django_db
def test_list_clients(auth_headers: dict[str, str], test_client) -> None:
    """GET /clients/clients returns clients."""
    response = client.get("/api/v1/clients/clients", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["count"] >= 1


@pytest.mark.django_db
def test_create_client(auth_headers: dict[str, str]) -> None:
    """POST /clients/clients creates a client."""
    payload = {
        "name": "API Client",
        "slug": "api-client",
        "industry": "saas",
        "status": "active",
        "tier": "standard",
        "contact_name": "John Smith",
        "contact_email": "john@example.com",
    }
    response = client.post(
        "/api/v1/clients/clients",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "API Client"


@pytest.mark.django_db
def test_get_client(auth_headers: dict[str, str], test_client) -> None:
    """GET /clients/clients/{client_id} returns a client."""
    response = client.get(f"/api/v1/clients/clients/{test_client.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Client"


@pytest.mark.django_db
def test_update_client(auth_headers: dict[str, str], test_client) -> None:
    """PUT /clients/clients/{client_id} updates a client."""
    payload = {"name": "Updated Client", "industry": "fintech"}
    response = client.put(
        f"/api/v1/clients/clients/{test_client.id}",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Client"


@pytest.mark.django_db
def test_delete_client(auth_headers: dict[str, str], test_client) -> None:
    """DELETE /clients/clients/{client_id} removes a client."""
    response = client.delete(f"/api/v1/clients/clients/{test_client.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True


@pytest.mark.django_db
def test_list_client_contacts(auth_headers: dict[str, str], test_client) -> None:
    """GET /clients/clients/{client_id}/contacts returns contacts."""
    ClientContact.objects.create(
        client=test_client, name="Alice", email="alice@example.com", role="manager"
    )
    response = client.get(f"/api/v1/clients/clients/{test_client.id}/contacts", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_client_contact(auth_headers: dict[str, str], test_client) -> None:
    """POST /clients/clients/{client_id}/contacts creates a contact."""
    payload = {"name": "Bob", "email": "bob@example.com", "phone": "", "role": "director"}
    response = client.post(
        f"/api/v1/clients/clients/{test_client.id}/contacts",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Bob"


@pytest.mark.django_db
def test_list_projects(auth_headers: dict[str, str], project: Project) -> None:
    """GET /clients/projects returns projects."""
    response = client.get("/api/v1/clients/projects", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
