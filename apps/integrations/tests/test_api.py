"""API tests for Integrations endpoints.

Tests connections, webhooks, sync under ``/api/v1/integrations/``.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.integrations.models import PlatformConnection, WebhookEndpoint, SyncLog

client = Client()


@pytest.fixture
def connection(tenant_id: str) -> PlatformConnection:
    """Create a test platform connection."""
    return PlatformConnection.objects.create(
        tenant_id=tenant_id,
        platform="twitter",
        connection_type="oauth2",
        display_name="Test Twitter Connection",
        status="active",
        connected_by="user-001",
    )


@pytest.fixture
def webhook(tenant_id: str, connection: PlatformConnection) -> WebhookEndpoint:
    """Create a test webhook endpoint."""
    return WebhookEndpoint.objects.create(
        connection=connection,
        name="Test Webhook",
        event_type="post.created",
        endpoint_url="https://example.com/webhook",
        is_active=True,
    )


@pytest.mark.django_db
def test_integrations_health_requires_auth() -> None:
    """GET /integrations/health without auth returns 401."""
    response = client.get("/api/v1/integrations/health")
    assert response.status_code == 401


@pytest.mark.django_db
def test_integrations_health(auth_headers: dict[str, str]) -> None:
    """GET /integrations/health returns module health."""
    response = client.get("/api/v1/integrations/health", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["module"] == "integrations"


@pytest.mark.django_db
def test_list_connections(auth_headers: dict[str, str], connection: PlatformConnection) -> None:
    """GET /integrations/connections returns connections."""
    response = client.get("/api/v1/integrations/connections", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


@pytest.mark.django_db
def test_create_connection(auth_headers: dict[str, str]) -> None:
    """POST /integrations/connections creates a connection."""
    payload = {
        "platform": "instagram",
        "connection_type": "oauth2",
        "display_name": "API Instagram Connection",
        "scopes_json": ["publish"],
        "metadata_json": {},
    }
    response = client.post(
        "/api/v1/integrations/connections",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "API Instagram Connection"


@pytest.mark.django_db
def test_get_connection(auth_headers: dict[str, str], connection: PlatformConnection) -> None:
    """GET /integrations/connections/{id} returns a connection."""
    response = client.get(f"/api/v1/integrations/connections/{connection.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Test Twitter Connection"


@pytest.mark.django_db
def test_delete_connection(auth_headers: dict[str, str], connection: PlatformConnection) -> None:
    """DELETE /integrations/connections/{id} removes a connection."""
    response = client.delete(f"/api/v1/integrations/connections/{connection.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True


@pytest.mark.django_db
def test_list_webhooks(auth_headers: dict[str, str], webhook: WebhookEndpoint) -> None:
    """GET /integrations/webhooks returns webhooks."""
    response = client.get("/api/v1/integrations/webhooks", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


@pytest.mark.django_db
def test_create_webhook(auth_headers: dict[str, str], connection: PlatformConnection) -> None:
    """POST /integrations/webhooks creates a webhook."""
    payload = {
        "name": "API Webhook",
        "event_type": "comment.received",
        "endpoint_url": "https://api.example.com/hook",
        "secret": "webhook-secret",
        "headers_json": {},
        "retry_policy_json": {},
        "filter_json": {},
    }
    response = client.post(
        "/api/v1/integrations/webhooks?connection_id=" + str(connection.id),
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_delete_webhook(auth_headers: dict[str, str], webhook: WebhookEndpoint) -> None:
    """DELETE /integrations/webhooks/{id} removes a webhook."""
    response = client.delete(f"/api/v1/integrations/webhooks/{webhook.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True


@pytest.mark.django_db
def test_list_sync_logs(auth_headers: dict[str, str]) -> None:
    """GET /integrations/sync-logs returns sync logs."""
    response = client.get("/api/v1/integrations/sync-logs", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
