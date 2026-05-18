"""Client portal API endpoints."""

from __future__ import annotations

from ninja import Router

from apps.clients.serializers import PortalCreateSchema, PortalSchema, PortalUpdateSchema
from apps.clients.services import PortalService
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/clients/{client_id}/portal", response=PortalSchema, tags=["Portals"])
def get_portal(request, client_id: int):
    """Retrieve the portal for a client."""
    portal = PortalService.get_by_client(client_id)
    return PortalSchema(
        id=portal.id,
        client_id=portal.client_id,
        slug=portal.slug,
        branding=portal.branding,
        custom_domain=portal.custom_domain,
        is_active=portal.is_active,
        created_at=portal.created_at,
        updated_at=portal.updated_at,
    )


@router.post("/clients/{client_id}/portal", response=PortalSchema, tags=["Portals"])
def create_portal(request, client_id: int, payload: PortalCreateSchema):
    """Create or get the portal for a client."""
    portal = PortalService.get_or_create(client_id, payload.dict())
    return PortalSchema(
        id=portal.id,
        client_id=portal.client_id,
        slug=portal.slug,
        branding=portal.branding,
        custom_domain=portal.custom_domain,
        is_active=portal.is_active,
        created_at=portal.created_at,
        updated_at=portal.updated_at,
    )


@router.put("/clients/{client_id}/portal", response=PortalSchema, tags=["Portals"])
def update_portal(request, client_id: int, payload: PortalUpdateSchema):
    """Update the portal for a client."""
    portal = PortalService.get_by_client(client_id)
    data = {k: v for k, v in payload.dict().items() if v is not None}
    updated = PortalService.update(portal, data)
    return PortalSchema(
        id=updated.id,
        client_id=updated.client_id,
        slug=updated.slug,
        branding=updated.branding,
        custom_domain=updated.custom_domain,
        is_active=updated.is_active,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.delete("/clients/{client_id}/portal", tags=["Portals"])
def delete_portal(request, client_id: int):
    """Delete the portal for a client."""
    portal = PortalService.get_by_client(client_id)
    PortalService.delete(portal)
    return {"success": True, "message": f"Portal for client {client_id} deleted"}
