"""Content Template endpoints.

GET  /api/v1/content/templates              — list templates
POST /api/v1/content/templates              — create template
GET  /api/v1/content/templates/{id}         — get template
PUT  /api/v1/content/templates/{id}         — update template
POST /api/v1/content/templates/{id}/render  — render template
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from django.db import models
from django.shortcuts import get_object_or_404
from ninja import Router

from apps.content_creation.models import ContentTemplate
from apps.content_creation.serializers import (
    ContentTemplateIn,
    ContentTemplateOut,
    RenderTemplateIn,
    RenderTemplateOut,
)
from apps.content_creation.services.templates import render_template
from apps.core.middleware import get_tenant_id, get_user_id

logger = logging.getLogger(__name__)

router = Router(tags=["Content Templates"])


@router.get("/templates", response=list[ContentTemplateOut])
def list_templates(request) -> list[ContentTemplate]:
    """List all templates for the current tenant (including public)."""
    tenant_id = get_tenant_id(request)
    return list(
        ContentTemplate.objects.filter(
            models.Q(tenant_id=tenant_id) | models.Q(is_public=True)
        ).order_by("-created_at")
    )


@router.post("/templates", response=ContentTemplateOut)
def create_template(request, payload: ContentTemplateIn) -> ContentTemplate:
    """Create a new content template."""
    tenant_id = get_tenant_id(request)
    user_id = get_user_id() or ""
    template = ContentTemplate.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        content_type=payload.content_type,
        body=payload.body,
        variables=payload.variables,
        default_values=payload.default_values,
        brand_kit_id=payload.brand_kit_id,
        created_by=user_id,
    )
    logger.info("Created template id=%s tenant=%s", template.id, tenant_id)
    return template


@router.get("/templates/{template_id}", response=ContentTemplateOut)
def get_template(request, template_id: UUID) -> ContentTemplate:
    """Retrieve a template by ID."""
    tenant_id = get_tenant_id(request)
    return get_object_or_404(
        ContentTemplate,
        models.Q(id=template_id, tenant_id=tenant_id) | models.Q(id=template_id, is_public=True),
    )


@router.put("/templates/{template_id}", response=ContentTemplateOut)
def update_template(request, template_id: UUID, payload: ContentTemplateIn) -> ContentTemplate:
    """Update a content template."""
    tenant_id = get_tenant_id(request)
    template = get_object_or_404(ContentTemplate, id=template_id, tenant_id=tenant_id)
    for field, value in payload.dict().items():
        setattr(template, field, value)
    template.save()
    logger.info("Updated template id=%s tenant=%s", template.id, tenant_id)
    return template


@router.delete("/templates/{template_id}")
def delete_template(request, template_id: UUID) -> dict[str, Any]:
    """Delete a content template."""
    tenant_id = get_tenant_id(request)
    template = get_object_or_404(ContentTemplate, id=template_id, tenant_id=tenant_id)
    template.delete()
    logger.info("Deleted template id=%s tenant=%s", template_id, tenant_id)
    return {"deleted": True, "id": str(template_id)}


@router.post("/templates/{template_id}/render", response=RenderTemplateOut)
def render_template_endpoint(
    request, template_id: UUID, payload: RenderTemplateIn
) -> dict[str, Any]:
    """Render a template with supplied variables.

    Substitutes variables into the Jinja2 template body and returns
    the rendered text along with any validation warnings.
    """
    tenant_id = get_tenant_id(request)
    template = get_object_or_404(
        ContentTemplate,
        models.Q(id=template_id, tenant_id=tenant_id) | models.Q(id=template_id, is_public=True),
    )

    # Increment usage count
    ContentTemplate.objects.filter(id=template_id).update(usage_count=models.F("usage_count") + 1)

    result = render_template(
        template_body=template.body,
        variables=payload.variables,
        var_defs=template.variables,
        platform=payload.platform,
        default_values=template.default_values,
    )

    return {
        "rendered": result["rendered"],
        "warnings": result["warnings"],
        "character_count": result["character_count"],
    }
