"""Content repurposing endpoints.

GET  /api/v1/content/repurposing-rules          — list rules
POST /api/v1/content/repurposing-rules          — create rule
POST /api/v1/content/generations/{id}/repurpose — repurpose content
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.content_creation.models import ContentGeneration, ContentRepurposingRule
from apps.content_creation.serializers import RepurposeIn, RepurposeOut
from apps.content_creation.services.repurposing import repurpose_content
from apps.core.middleware import get_tenant_id

logger = logging.getLogger(__name__)

router = Router(tags=["Content Repurposing"])


@router.get("/repurposing-rules", response=list[dict[str, Any]])
def list_repurposing_rules(request) -> list[ContentRepurposingRule]:
    """List all active repurposing rules for the current tenant."""
    tenant_id = get_tenant_id(request)
    return list(
        ContentRepurposingRule.objects.filter(tenant_id=tenant_id, is_active=True).order_by(
            "-created_at"
        )
    )


@router.post("/repurposing-rules")
def create_repurposing_rule(request, payload: dict[str, Any]) -> dict[str, Any]:
    """Create a new content repurposing rule."""
    tenant_id = get_tenant_id(request)
    rule = ContentRepurposingRule.objects.create(
        tenant_id=tenant_id,
        name=payload.get("name", ""),
        description=payload.get("description", ""),
        source_format=payload.get("source_format", "blog"),
        target_formats=payload.get("target_formats", []),
        transformation_rules=payload.get("transformation_rules", {}),
        is_active=payload.get("is_active", True),
    )
    logger.info("Created repurposing rule id=%s tenant=%s", rule.id, tenant_id)
    return {"id": str(rule.id), "name": rule.name, "created": True}


@router.post("/generations/{generation_id}/repurpose", response=RepurposeOut)
def repurpose_generation(
    request,
    generation_id: UUID,
    payload: RepurposeIn,
) -> dict[str, Any]:
    """Repurpose a content generation into a different format.

    Takes the body text of an existing generation and transforms it
    according to the requested target formats using the repurposing
    engine's transformation rules.
    """
    tenant_id = get_tenant_id(request)
    gen = get_object_or_404(ContentGeneration, id=generation_id, tenant_id=tenant_id)

    if not gen.body_text:
        return {
            "source_format": gen.content_type,
            "target_format": ", ".join(payload.target_formats) if payload.target_formats else "",
            "transformed_text": "",
            "character_count": 0,
            "warnings": ["Source content has no body text to repurpose"],
        }

    target_format = payload.target_formats[0] if payload.target_formats else "blog"

    result = repurpose_content(
        source_text=gen.body_text,
        source_format=gen.content_type,
        target_format=target_format,
        transformation_rules=payload.transformation_rules,
    )

    # Create a new generation record for the repurposed content
    new_gen = ContentGeneration.objects.create(
        title=f"Repurposed: {gen.title}"[:255],
        prompt=gen.prompt,
        content_type=ContentGeneration.ContentType.TEXT,
        status=ContentGeneration.Status.DRAFT,
        body_text=result["transformed_text"],
        model_used="repurposing-engine",
        tenant_id=tenant_id,
        created_by="system",
    )

    logger.info(
        "Repurposed generation %s -> %s (new id=%s)",
        generation_id,
        target_format,
        new_gen.id,
    )

    return {
        "source_format": result.get("source_format", gen.content_type),
        "target_format": result.get("target_format", target_format),
        "transformed_text": result["transformed_text"],
        "character_count": result["character_count"],
        "warnings": result.get("warnings", []),
        "new_generation_id": str(new_gen.id),
    }
