"""Communication log API endpoints."""

from __future__ import annotations

from ninja import Router

from apps.clients.serializers import (
    CommunicationCreateSchema,
    CommunicationSchema,
    CommunicationUpdateSchema,
    PaginatedCommunicationsSchema,
)
from apps.clients.services import CommunicationService
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


def _get_tenant(request) -> str:
    """Extract tenant_id from the authenticated user."""
    return getattr(request.auth, "tenant_id", "default")


@router.get("/communications", response=PaginatedCommunicationsSchema, tags=["Communications"])
def list_communications(
    request,
    client_id: int | None = None,
    comm_type: str | None = None,
    project_id: int | None = None,
):
    """List communication logs for the current tenant."""
    tenant_id = _get_tenant(request)
    qs = CommunicationService.list_communications(tenant_id, client_id, comm_type, project_id)
    items = list(qs[:100])
    return PaginatedCommunicationsSchema(
        count=qs.count(),
        items=[
            CommunicationSchema(
                id=c.id,
                tenant_id=c.tenant_id,
                client_id=c.client_id,
                project_id=c.project_id,
                comm_type=c.comm_type,
                direction=c.direction,
                subject=c.subject,
                content=c.content,
                participant_ids=c.participant_ids,
                duration_minutes=c.duration_minutes,
                metadata=c.metadata,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in items
        ],
    )


@router.get(
    "/clients/{client_id}/communications",
    response=PaginatedCommunicationsSchema,
    tags=["Communications"],
)
def list_client_communications(request, client_id: int):
    """List communication logs for a specific client."""
    tenant_id = _get_tenant(request)
    qs = CommunicationService.list_communications(tenant_id, client_id)
    items = list(qs[:100])
    return PaginatedCommunicationsSchema(
        count=qs.count(),
        items=[
            CommunicationSchema(
                id=c.id,
                tenant_id=c.tenant_id,
                client_id=c.client_id,
                project_id=c.project_id,
                comm_type=c.comm_type,
                direction=c.direction,
                subject=c.subject,
                content=c.content,
                participant_ids=c.participant_ids,
                duration_minutes=c.duration_minutes,
                metadata=c.metadata,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in items
        ],
    )


@router.post(
    "/clients/{client_id}/communications",
    response=CommunicationSchema,
    tags=["Communications"],
)
def create_communication(request, client_id: int, payload: CommunicationCreateSchema):
    """Create a communication log entry."""
    tenant_id = _get_tenant(request)
    data = payload.dict()
    log = CommunicationService.create(tenant_id, client_id, data)
    return CommunicationSchema(
        id=log.id,
        tenant_id=log.tenant_id,
        client_id=log.client_id,
        project_id=log.project_id,
        comm_type=log.comm_type,
        direction=log.direction,
        subject=log.subject,
        content=log.content,
        participant_ids=log.participant_ids,
        duration_minutes=log.duration_minutes,
        metadata=log.metadata,
        created_at=log.created_at,
        updated_at=log.updated_at,
    )


@router.put(
    "/communications/{log_id}",
    response=CommunicationSchema,
    tags=["Communications"],
)
def update_communication(request, log_id: int, payload: CommunicationUpdateSchema):
    """Update a communication log entry."""
    tenant_id = _get_tenant(request)
    log = CommunicationService.get_by_id(tenant_id, log_id)
    data = {k: v for k, v in payload.dict().items() if v is not None}
    updated = CommunicationService.update(log, data)
    return CommunicationSchema(
        id=updated.id,
        tenant_id=updated.tenant_id,
        client_id=updated.client_id,
        project_id=updated.project_id,
        comm_type=updated.comm_type,
        direction=updated.direction,
        subject=updated.subject,
        content=updated.content,
        participant_ids=updated.participant_ids,
        duration_minutes=updated.duration_minutes,
        metadata=updated.metadata,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.delete("/communications/{log_id}", tags=["Communications"])
def delete_communication(request, log_id: int):
    """Delete a communication log entry."""
    tenant_id = _get_tenant(request)
    log = CommunicationService.get_by_id(tenant_id, log_id)
    CommunicationService.delete(log)
    return {"success": True, "message": f"Communication {log_id} deleted"}
