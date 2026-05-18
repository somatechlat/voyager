"""Email template CRUD and builder views."""

from __future__ import annotations

import logging
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.email_marketing.models.template import EmailTemplate
from apps.email_marketing.serializers import (
    CompatibilityResultSchema,
    EmailTemplateCreateSchema,
    EmailTemplateDetailSchema,
    EmailTemplateListSchema,
    EmailTemplateRenderSchema,
    EmailTemplateUpdateSchema,
)
from apps.email_marketing.services.templates import (
    generate_plain_text,
    render_template_html,
    test_compatibility,
)

logger = logging.getLogger(__name__)

router = Router()


@router.get("/", response=list[EmailTemplateListSchema])
def list_templates(
    request,
    tenant_id: str = "",
    category: str = "",
    search: str = "",
    limit: int = 50,
    offset: int = 0,
) -> list[EmailTemplate]:
    """List email templates with optional filtering.

    Args:
        request: HTTP request.
        tenant_id: Filter by tenant.
        category: Filter by template category.
        search: Search in name.
        limit: Page size.
        offset: Pagination offset.

    Returns:
        List of email templates.
    """
    qs = EmailTemplate.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if category:
        qs = qs.filter(category=category)
    if search:
        qs = qs.filter(name__icontains=search)
    return list(qs.order_by("-created_at")[offset : offset + limit])


@router.post("/", response=EmailTemplateDetailSchema)
def create_template(
    request,
    payload: EmailTemplateCreateSchema,
) -> EmailTemplate:
    """Create a new email template.

    Args:
        request: HTTP request.
        payload: Template creation data.

    Returns:
        Created template.
    """
    data = payload.dict()
    blocks = data.pop("blocks", None)
    if blocks:
        data["json_design"] = {"blocks": blocks}
        data["html"] = render_template_html(
            blocks=blocks,
            brand_kit=data.get("brand_kit"),
            preheader=data.get("preheader_text", ""),
            title=data.get("name", ""),
        )
    if not data.get("plain_text"):
        data["plain_text"] = generate_plain_text(data.get("html", ""))
    template = EmailTemplate.objects.create(**data)
    logger.info("Template %s created for tenant %s", template.id, template.tenant_id)
    return template


@router.get("/{template_id}", response=EmailTemplateDetailSchema)
def get_template(
    request,
    template_id: int,
) -> EmailTemplate:
    """Get a single email template.

    Args:
        request: HTTP request.
        template_id: Template primary key.

    Returns:
        Email template.
    """
    return get_object_or_404(EmailTemplate, id=template_id)


@router.put("/{template_id}", response=EmailTemplateDetailSchema)
def update_template(
    request,
    template_id: int,
    payload: EmailTemplateUpdateSchema,
) -> EmailTemplate:
    """Update an email template.

    Args:
        request: HTTP request.
        template_id: Template primary key.
        payload: Update data.

    Returns:
        Updated template.
    """
    template = get_object_or_404(EmailTemplate, id=template_id)
    data = payload.dict(exclude_unset=True)
    blocks = data.pop("blocks", None)
    if blocks is not None:
        template.json_design = {"blocks": blocks}
        template.html = render_template_html(
            blocks=blocks,
            brand_kit=data.get("brand_kit", template.brand_kit),
            preheader=data.get("preheader_text", template.preheader_text),
            title=data.get("name", template.name),
        )
        template.plain_text = generate_plain_text(template.html)
    for attr, val in data.items():
        setattr(template, attr, val)
    template.save()
    return template


@router.delete("/{template_id}")
def delete_template(
    request,
    template_id: int,
) -> dict[str, bool]:
    """Delete an email template.

    Args:
        request: HTTP request.
        template_id: Template primary key.

    Returns:
        Success dict.
    """
    template = get_object_or_404(EmailTemplate, id=template_id)
    template.delete()
    return {"success": True}


@router.post("/{template_id}/render", response=dict[str, str])
def render_template(
    request,
    template_id: int,
    payload: EmailTemplateRenderSchema,
) -> dict[str, str]:
    """Render a template to HTML with optional personalization.

    Args:
        request: HTTP request.
        template_id: Template primary key.
        payload: Render options.

    Returns:
        Dict with html and plain_text keys.
    """
    template = get_object_or_404(EmailTemplate, id=template_id)
    design = template.json_design or {}
    blocks = design.get("blocks", [])
    brand = payload.brand_kit or template.brand_kit
    html_output = render_template_html(
        blocks=blocks,
        brand_kit=brand,
        preheader=payload.preheader or template.preheader_text,
        title=template.name,
    )
    return {
        "html": html_output,
        "plain_text": generate_plain_text(html_output),
    }


@router.post("/{template_id}/compatibility", response=CompatibilityResultSchema)
def check_compatibility(
    request,
    template_id: int,
) -> dict[str, Any]:
    """Test email template compatibility across clients.

    Args:
        request: HTTP request.
        template_id: Template primary key.

    Returns:
        Compatibility test results.
    """
    template = get_object_or_404(EmailTemplate, id=template_id)
    result = test_compatibility(template.html)
    template.compatibility_score = result["overall_score"]
    template.compatibility_results = result
    template.save(update_fields=["compatibility_score", "compatibility_results"])
    return result


@router.get("/{template_id}/duplicate", response=EmailTemplateDetailSchema)
def duplicate_template(
    request,
    template_id: int,
) -> EmailTemplate:
    """Duplicate an email template.

    Args:
        request: HTTP request.
        template_id: Template primary key.

    Returns:
        New duplicated template.
    """
    template = get_object_or_404(EmailTemplate, id=template_id)
    template.pk = None
    template.name = f"{template.name} (Copy)"
    template.compatibility_score = None
    template.compatibility_results = {}
    template.save()
    return template
