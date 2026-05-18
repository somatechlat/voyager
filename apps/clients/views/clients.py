"""Client, contact, and onboarding API endpoints."""

from __future__ import annotations

import logging

from ninja import Router
from ninja.errors import HttpError

from apps.clients.models.client import Client, ClientContact
from apps.clients.serializers import (
    ClientContactCreateSchema,
    ClientContactSchema,
    ClientContactUpdateSchema,
    ClientCreateSchema,
    ClientDetailSchema,
    ClientListSchema,
    ClientUpdateSchema,
    OnboardingCompleteSchema,
    OnboardingResponseSchema,
    PaginatedClientsSchema,
)
from apps.clients.services import ClientService
from apps.rbac.auth import VoyagerKeycloakBearer

logger = logging.getLogger(__name__)
router = Router(auth=VoyagerKeycloakBearer())


def _get_tenant(request) -> str:
    """Extract tenant_id from the authenticated user."""
    return getattr(request.auth, "tenant_id", "default")


# ============================================================================
# Client CRUD
# ============================================================================


@router.get("/clients", response=PaginatedClientsSchema, tags=["Clients"])
def list_clients(
    request,
    status: str | None = None,
    tier: str | None = None,
    search: str | None = None,
):
    """List all clients for the current tenant."""
    tenant_id = _get_tenant(request)
    qs = ClientService.list_clients(tenant_id, status, tier, search)
    items = list(qs[:100])
    return PaginatedClientsSchema(
        count=qs.count(),
        items=[
            ClientListSchema(
                id=c.id,
                name=c.name,
                slug=c.slug,
                industry=c.industry,
                status=c.status,
                tier=c.tier,
                contact_name=c.contact_name,
                contact_email=c.contact_email,
                created_at=c.created_at,
            )
            for c in items
        ],
    )


@router.post("/clients", response=ClientDetailSchema, tags=["Clients"])
def create_client(request, payload: ClientCreateSchema):
    """Create a new client."""
    tenant_id = _get_tenant(request)
    data = payload.dict()
    client = ClientService.create(tenant_id, data)
    return client


@router.get("/clients/{client_id}", response=ClientDetailSchema, tags=["Clients"])
def get_client(request, client_id: int):
    """Retrieve a single client by ID."""
    tenant_id = _get_tenant(request)
    return ClientService.get_by_id(tenant_id, client_id)


@router.put("/clients/{client_id}", response=ClientDetailSchema, tags=["Clients"])
def update_client(request, client_id: int, payload: ClientUpdateSchema):
    """Update an existing client."""
    tenant_id = _get_tenant(request)
    client = ClientService.get_by_id(tenant_id, client_id)
    data = {k: v for k, v in payload.dict().items() if v is not None}
    return ClientService.update(client, data)


@router.delete("/clients/{client_id}", tags=["Clients"])
def delete_client(request, client_id: int):
    """Delete a client and all related data."""
    tenant_id = _get_tenant(request)
    client = ClientService.get_by_id(tenant_id, client_id)
    ClientService.delete(client)
    return {"success": True, "message": f"Client {client_id} deleted"}


@router.post(
    "/clients/{client_id}/status/{status}",
    response=ClientDetailSchema,
    tags=["Clients"],
)
def set_client_status(request, client_id: int, status: str):
    """Transition a client to a new status."""
    tenant_id = _get_tenant(request)
    client = ClientService.get_by_id(tenant_id, client_id)
    return ClientService.transition_status(client, status)


# ============================================================================
# Onboarding
# ============================================================================


@router.post(
    "/clients/{client_id}/onboarding/complete",
    response=OnboardingResponseSchema,
    tags=["Clients"],
)
def complete_onboarding(
    request, client_id: int, payload: OnboardingCompleteSchema
):
    """Complete the onboarding process for a client."""
    tenant_id = _get_tenant(request)
    client = ClientService.complete_onboarding(
        tenant_id, client_id, payload.dict().get("onboarding_data")
    )
    return OnboardingResponseSchema(
        client_id=client.id,
        status=client.status,
        completed_at=client.updated_at,
        message="Onboarding completed successfully",
    )


@router.post("/clients/onboarding/start", response=ClientDetailSchema, tags=["Clients"])
def start_onboarding(request, payload: ClientCreateSchema):
    """Start the onboarding process for a new client."""
    tenant_id = _get_tenant(request)
    data = payload.dict()
    return ClientService.start_onboarding(tenant_id, data)


# ============================================================================
# Client contacts
# ============================================================================


@router.get(
    "/clients/{client_id}/contacts",
    response=list[ClientContactSchema],
    tags=["Clients"],
)
def list_client_contacts(request, client_id: int):
    """List all contacts for a client."""
    tenant_id = _get_tenant(request)
    ClientService.get_by_id(tenant_id, client_id)
    contacts = ClientContact.objects.filter(client_id=client_id)
    return [
        ClientContactSchema(
            id=c.id,
            client_id=c.client_id,
            name=c.name,
            email=c.email,
            phone=c.phone,
            role=c.role,
            is_primary=c.is_primary,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in contacts
    ]


@router.post(
    "/clients/{client_id}/contacts",
    response=ClientContactSchema,
    tags=["Clients"],
)
def create_client_contact(
    request, client_id: int, payload: ClientContactCreateSchema
):
    """Create a contact for a client."""
    tenant_id = _get_tenant(request)
    client = ClientService.get_by_id(tenant_id, client_id)
    data = payload.dict()
    contact = ClientContact.objects.create(client=client, **data)
    return ClientContactSchema(
        id=contact.id,
        client_id=contact.client_id,
        name=contact.name,
        email=contact.email,
        phone=contact.phone,
        role=contact.role,
        is_primary=contact.is_primary,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
    )


@router.put(
    "/clients/{client_id}/contacts/{contact_id}",
    response=ClientContactSchema,
    tags=["Clients"],
)
def update_client_contact(
    request,
    client_id: int,
    contact_id: int,
    payload: ClientContactUpdateSchema,
):
    """Update a client contact."""
    tenant_id = _get_tenant(request)
    ClientService.get_by_id(tenant_id, client_id)
    try:
        contact = ClientContact.objects.get(client_id=client_id, id=contact_id)
    except ClientContact.DoesNotExist:
        raise HttpError(404, "Contact not found")
    for key, value in payload.dict().items():
        if value is not None:
            setattr(contact, key, value)
    contact.save()
    return ClientContactSchema(
        id=contact.id,
        client_id=contact.client_id,
        name=contact.name,
        email=contact.email,
        phone=contact.phone,
        role=contact.role,
        is_primary=contact.is_primary,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
    )


@router.delete("/clients/{client_id}/contacts/{contact_id}", tags=["Clients"])
def delete_client_contact(request, client_id: int, contact_id: int):
    """Delete a client contact."""
    tenant_id = _get_tenant(request)
    ClientService.get_by_id(tenant_id, client_id)
    try:
        contact = ClientContact.objects.get(client_id=client_id, id=contact_id)
    except ClientContact.DoesNotExist:
        raise HttpError(404, "Contact not found")
    contact.delete()
    return {"success": True, "message": f"Contact {contact_id} deleted"}
