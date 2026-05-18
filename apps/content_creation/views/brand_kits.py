"""Brand Kit endpoints.

GET    /api/v1/content/brand-kits          — list brand kits
POST   /api/v1/content/brand-kits          — create brand kit
GET    /api/v1/content/brand-kits/{id}     — get brand kit
PUT    /api/v1/content/brand-kits/{id}     — update brand kit
DELETE /api/v1/content/brand-kits/{id}     — delete brand kit
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.content_creation.models import BrandKit
from apps.content_creation.serializers import BrandKitIn, BrandKitOut
from apps.core.middleware import get_tenant_id

logger = logging.getLogger(__name__)

router = Router(tags=["Brand Kits"])


@router.get("/brand-kits", response=list[BrandKitOut])
def list_brand_kits(request) -> list[BrandKit]:
    """List all brand kits for the current tenant."""
    tenant_id = get_tenant_id(request)
    return list(BrandKit.objects.filter(tenant_id=tenant_id).order_by("-created_at"))


@router.post("/brand-kits", response=BrandKitOut)
def create_brand_kit(request, payload: BrandKitIn) -> BrandKit:
    """Create a new brand kit."""
    tenant_id = get_tenant_id(request)
    kit = BrandKit.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        voice=payload.voice,
        tone_rules=payload.tone_rules,
        forbidden_words=payload.forbidden_words,
        required_phrases=payload.required_phrases,
        color_palette=payload.color_palette,
        logo_url=payload.logo_url,
        font_preferences=payload.font_preferences,
        competitor_list=payload.competitor_list,
        avoid_topics=payload.avoid_topics,
        target_audience=payload.target_audience,
        min_readability=payload.min_readability,
        min_compliance_score=payload.min_compliance_score,
    )
    logger.info("Created brand kit id=%s tenant=%s", kit.id, tenant_id)
    return kit


@router.get("/brand-kits/{kit_id}", response=BrandKitOut)
def get_brand_kit(request, kit_id: UUID) -> BrandKit:
    """Retrieve a brand kit by ID."""
    tenant_id = get_tenant_id(request)
    return get_object_or_404(BrandKit, id=kit_id, tenant_id=tenant_id)


@router.put("/brand-kits/{kit_id}", response=BrandKitOut)
def update_brand_kit(request, kit_id: UUID, payload: BrandKitIn) -> BrandKit:
    """Update a brand kit."""
    tenant_id = get_tenant_id(request)
    kit = get_object_or_404(BrandKit, id=kit_id, tenant_id=tenant_id)
    for field, value in payload.dict().items():
        setattr(kit, field, value)
    kit.save()
    logger.info("Updated brand kit id=%s tenant=%s", kit.id, tenant_id)
    return kit


@router.delete("/brand-kits/{kit_id}")
def delete_brand_kit(request, kit_id: UUID) -> dict[str, Any]:
    """Delete a brand kit."""
    tenant_id = get_tenant_id(request)
    kit = get_object_or_404(BrandKit, id=kit_id, tenant_id=tenant_id)
    kit.delete()
    logger.info("Deleted brand kit id=%s tenant=%s", kit_id, tenant_id)
    return {"deleted": True, "id": str(kit_id)}
