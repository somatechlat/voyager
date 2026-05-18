"""Audience Persona views — SP-001.

CRUD endpoints and campaign linking for audience personas.
"""

from __future__ import annotations

import logging
from typing import Any

from ninja import Query, Router

from apps.strategy.models import AudiencePersona, PersonaCampaignLink
from apps.strategy.serializers.personas import (
    PersonaCampaignLinkIn,
    PersonaCampaignLinkOut,
    PersonaFilter,
    PersonaIn,
    PersonaOut,
)
from apps.strategy.services.personas import PersonaService

logger = logging.getLogger(__name__)

router = Router(tags=["Strategy / Personas"])


def _get_tenant_id(request) -> str:
    return getattr(request, "tenant_id", "default")


def _persona_to_dict(persona: AudiencePersona) -> dict[str, Any]:
    return {
        "id": str(persona.id),
        "name": persona.name,
        "description": persona.description or "",
        "demographics": persona.demographics or {},
        "psychographics": persona.psychographics or {},
        "pain_points": persona.pain_points or [],
        "content_preferences": persona.content_preferences or {},
        "channel_preferences": persona.channel_preferences or [],
        "data_sources": persona.data_sources or [],
        "is_active": persona.is_active,
        "created_at": persona.created_at,
        "updated_at": persona.updated_at,
    }


@router.post("/personas", response=PersonaOut)
def create_persona(request, payload: PersonaIn):
    """Create a new audience persona."""
    tenant_id = _get_tenant_id(request)
    persona = PersonaService.create_persona(
        tenant_id=tenant_id,
        name=payload.name,
        demographics=payload.demographics,
        description=payload.description,
        psychographics=payload.psychographics,
        pain_points=payload.pain_points,
        content_preferences=payload.content_preferences,
        channel_preferences=payload.channel_preferences,
        data_sources=payload.data_sources,
    )
    return _persona_to_dict(persona)


@router.get("/personas", response=list[PersonaOut])
def list_personas(request, filters: Query[PersonaFilter]):
    """List personas for the tenant with optional filtering."""
    tenant_id = _get_tenant_id(request)
    qs = AudiencePersona.objects.filter(tenant_id=tenant_id)
    if filters.is_active is not None:
        qs = qs.filter(is_active=filters.is_active)
    if filters.search:
        qs = qs.filter(name__icontains=filters.search)
    qs = qs.order_by("-created_at")[filters.offset : filters.offset + filters.limit]
    return [_persona_to_dict(p) for p in qs]


@router.get("/personas/{persona_id}", response=PersonaOut)
def get_persona(request, persona_id: str):
    """Get a single persona by ID."""
    tenant_id = _get_tenant_id(request)
    persona = AudiencePersona.objects.get(id=persona_id, tenant_id=tenant_id)
    return _persona_to_dict(persona)


@router.put("/personas/{persona_id}", response=PersonaOut)
def update_persona(request, persona_id: str, payload: PersonaIn):
    """Update an existing persona."""
    tenant_id = _get_tenant_id(request)
    updates = payload.model_dump(exclude_unset=True)
    persona = PersonaService.update_persona(
        persona_id=persona_id,
        tenant_id=tenant_id,
        **updates,
    )
    return _persona_to_dict(persona)


@router.delete("/personas/{persona_id}")
def delete_persona(request, persona_id: str):
    """Soft-delete a persona by setting is_active=False."""
    tenant_id = _get_tenant_id(request)
    persona = AudiencePersona.objects.get(id=persona_id, tenant_id=tenant_id)
    persona.is_active = False
    persona.save(update_fields=["is_active", "updated_at"])
    return {"success": True, "id": str(persona_id), "action": "deactivated"}


@router.post("/personas/{persona_id}/link-campaign", response=PersonaCampaignLinkOut)
def link_persona_to_campaign(
    request,
    persona_id: str,
    payload: PersonaCampaignLinkIn,
):
    """Link a persona to a campaign with a weight."""
    link = PersonaService.link_to_campaign(
        persona_id=persona_id,
        campaign_id=payload.campaign_id,
        weight=payload.weight,
    )
    return {
        "id": str(link.id),
        "persona_id": str(link.persona_id),
        "campaign_id": str(link.campaign_id),
        "weight": link.weight,
        "created_at": link.created_at,
    }


@router.get("/personas/{persona_id}/campaigns")
def get_persona_campaigns(request, persona_id: str):
    """Get all campaigns linked to a persona."""
    tenant_id = _get_tenant_id(request)
    links = (
        PersonaCampaignLink.objects.filter(
            persona_id=persona_id,
            persona__tenant_id=tenant_id,
        )
        .select_related("persona")
        .order_by("-weight")
    )
    return {
        "persona_id": persona_id,
        "campaigns": [
            {
                "campaign_id": str(link.campaign_id),
                "weight": float(link.weight),
                "linked_at": link.created_at,
            }
            for link in links
        ],
    }


@router.get("/personas/aggregate-targeting")
def aggregate_targeting(request, persona_ids: str):
    """Aggregate demographic targeting from multiple persona IDs.

    Query param: persona_ids=comma-separated UUIDs
    """
    ids = [pid.strip() for pid in persona_ids.split(",") if pid.strip()]
    result = PersonaService.aggregate_targeting(ids)
    return result or {
        "age_range": {"min": None, "max": None},
        "gender": [],
        "languages": [],
        "locations": [],
        "persona_count": 0,
    }
