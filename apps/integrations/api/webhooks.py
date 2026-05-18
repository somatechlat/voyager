"""Webhook management endpoints."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from django.shortcuts import get_object_or_404

from apps.integrations.api import router
from apps.integrations.api.helpers import (
    get_tenant_id,
    webhook_endpoint_out,
)
from apps.integrations.models import WebhookDelivery, WebhookEndpoint
from apps.integrations.serializers import (
    WebhookEndpointCreateIn,
    WebhookReceiveOut,
)
from apps.integrations.services.webhooks import (
    create_webhook_endpoint,
    receive_webhook,
)


@router.post(
    "/webhooks/receive/{platform}",
    response={200: WebhookReceiveOut},
    tags=["Integrations"],
    auth=None,
)
def receive_inbound_webhook(request: HttpRequest, platform: str) -> dict[str, Any]:
    """Receive an inbound webhook from an external platform (public endpoint)."""
    return receive_webhook(platform, dict(request.headers), request.body)


@router.get("/webhooks", response={200: dict}, tags=["Integrations"])
def list_webhooks(
    request: HttpRequest,
    connection_id: str | None = None,
    is_active: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """List webhook endpoints."""
    qs = WebhookEndpoint.objects.filter(connection__tenant_id=get_tenant_id(request))
    if connection_id:
        qs = qs.filter(connection_id=connection_id)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    total = qs.count()
    items = qs.order_by("-created_at")[offset : offset + limit]
    return {
        "items": [webhook_endpoint_out(w) for w in items],
        "total": total,
    }


@router.post("/webhooks", response={200: dict}, tags=["Integrations"])
def create_webhook(request: HttpRequest, payload: WebhookEndpointCreateIn) -> dict[str, Any]:
    """Create a new webhook endpoint."""
    connection_id = request.GET.get("connection_id", "")
    endpoint = create_webhook_endpoint(
        connection_id=connection_id,
        name=payload.name,
        event_type=payload.event_type,
        endpoint_url=payload.endpoint_url,
        secret=payload.secret,
        headers_json=payload.headers_json,
        retry_policy_json=payload.retry_policy_json,
        filter_json=payload.filter_json,
    )
    return webhook_endpoint_out(endpoint)


@router.get("/webhooks/{webhook_id}", response={200: dict}, tags=["Integrations"])
def get_webhook(request: HttpRequest, webhook_id: str) -> dict[str, Any]:
    """Get a webhook endpoint by ID."""
    endpoint = get_object_or_404(
        WebhookEndpoint, id=webhook_id, connection__tenant_id=get_tenant_id(request)
    )
    return webhook_endpoint_out(endpoint)


@router.delete("/webhooks/{webhook_id}", tags=["Integrations"])
def delete_webhook(request: HttpRequest, webhook_id: str) -> dict[str, bool]:
    """Delete a webhook endpoint."""
    endpoint = get_object_or_404(
        WebhookEndpoint, id=webhook_id, connection__tenant_id=get_tenant_id(request)
    )
    endpoint.delete()
    return {"success": True}


@router.get("/webhooks/{webhook_id}/deliveries", response={200: dict}, tags=["Integrations"])
def get_webhook_deliveries(
    request: HttpRequest,
    webhook_id: str,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """List deliveries for a webhook endpoint."""
    qs = WebhookDelivery.objects.filter(webhook_id=webhook_id)
    if status:
        qs = qs.filter(status=status)
    total = qs.count()
    items = qs.order_by("-created_at")[offset : offset + limit]
    return {
        "items": [
            {
                "id": str(d.id),
                "webhook_id": str(d.webhook_id),
                "event_type": d.event_type,
                "status": d.status,
                "response_status": d.response_status,
                "attempt_count": d.attempt_count,
                "delivered_at": d.delivered_at,
                "created_at": d.created_at,
            }
            for d in items
        ],
        "total": total,
    }
