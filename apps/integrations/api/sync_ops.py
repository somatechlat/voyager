"""Sync operation endpoints."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from django.shortcuts import get_object_or_404

from apps.integrations.api import router
from apps.integrations.api.helpers import get_tenant_id, sync_log_out
from apps.integrations.models import PlatformConnection, SyncLog
from apps.integrations.serializers import SyncTriggerIn
from apps.integrations.services.sync import run_sync_for_connection


@router.post("/connections/{connection_id}/sync", response={200: dict}, tags=["Integrations"])
def trigger_sync(
    request: HttpRequest, connection_id: str, payload: SyncTriggerIn
) -> dict[str, Any]:
    """Trigger a data sync for a connection."""
    conn = get_object_or_404(PlatformConnection, id=connection_id, tenant_id=get_tenant_id(request))
    return run_sync_for_connection(
        connection=conn,
        sync_type=payload.sync_type,
        direction=payload.direction,
        conflict_resolution=payload.conflict_resolution,
        field_mappings_json=payload.field_mappings_json,
        source_data=payload.source_data,
        target_data=payload.target_data,
    )


@router.get("/sync-logs", response={200: dict}, tags=["Integrations"])
def list_sync_logs(
    request: HttpRequest,
    connection_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """List sync logs."""
    qs = SyncLog.objects.filter(connection__tenant_id=get_tenant_id(request))
    if connection_id:
        qs = qs.filter(connection_id=connection_id)
    if status:
        qs = qs.filter(status=status)
    total = qs.count()
    items = qs.order_by("-created_at")[offset : offset + limit]
    return {"items": [sync_log_out(s) for s in items], "total": total}


@router.get("/sync-logs/{sync_log_id}", response={200: dict}, tags=["Integrations"])
def get_sync_log(request: HttpRequest, sync_log_id: str) -> dict[str, Any]:
    """Get a single sync log entry."""
    log = get_object_or_404(SyncLog, id=sync_log_id, connection__tenant_id=get_tenant_id(request))
    return sync_log_out(log)
