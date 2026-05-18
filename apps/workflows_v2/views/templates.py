"""Template marketplace views."""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.workflows_v2.models.template import WorkflowTemplate
from apps.workflows_v2.serializers import (
    ErrorSchema,
    TemplateCreateSchema,
    TemplateInstallSchema,
    TemplateListSchema,
    TemplateOutSchema,
)
from apps.workflows_v2.services.templates import (
    export_template,
    import_template,
    install_template,
    list_templates,
    publish_template,
)

router = Router(auth=VoyagerKeycloakBearer())


def _get_tenant(request) -> str:
    """Extract tenant_id from request."""
    return getattr(request, "tenant_id", "") or getattr(request.auth, "tenant_id", "default")


def _get_user(request) -> str:
    """Extract user_id from request."""
    return getattr(request.auth, "sub", "anonymous")


@router.get("/marketplace", response=list[TemplateListSchema], tags=["Templates"])
def marketplace(
    request,
    category: str | None = None,
    search: str | None = None,
) -> list[WorkflowTemplate]:
    """List available workflow templates in the marketplace."""
    return list_templates(category=category, search=search)


@router.get(
    "/marketplace/{template_id}",
    response=TemplateOutSchema,
    tags=["Templates"],
)
def template_detail(request, template_id: int) -> WorkflowTemplate:
    """Get detailed template information."""
    return get_object_or_404(WorkflowTemplate, id=template_id)


@router.post(
    "/marketplace",
    response=TemplateOutSchema,
    tags=["Templates"],
)
def create_template(request, payload: TemplateCreateSchema) -> WorkflowTemplate:
    """Publish a new workflow template."""
    user_id = _get_user(request)
    return publish_template(
        name=payload.name,
        description=payload.description,
        category=payload.category,
        author=user_id,
        workflow_definition=payload.workflow,
        configurable=payload.configurable,
        required_modules=payload.required_modules,
        tags=payload.tags,
        icon=payload.icon,
    )


@router.post(
    "/marketplace/{template_id}/install",
    response=dict,
    tags=["Templates"],
)
def install_template_view(
    request,
    template_id: int,
    payload: TemplateInstallSchema,
) -> dict[str, Any]:
    """Install a template as a new workflow."""
    tenant_id = _get_tenant(request)
    user_id = _get_user(request)
    template = get_object_or_404(WorkflowTemplate, id=template_id)
    workflow = install_template(
        template=template,
        tenant_id=tenant_id,
        created_by=user_id,
        customizations=payload.customizations,
    )
    return {
        "status": "installed",
        "template_id": template_id,
        "workflow_id": workflow.id,
        "workflow_name": workflow.name,
    }


@router.get(
    "/marketplace/{template_id}/export",
    response=dict,
    tags=["Templates"],
)
def export_template_view(request, template_id: int) -> dict[str, Any]:
    """Export a template to portable JSON."""
    template = get_object_or_404(WorkflowTemplate, id=template_id)
    return export_template(template)


@router.post(
    "/marketplace/import",
    response=TemplateOutSchema,
    tags=["Templates"],
)
def import_template_view(
    request,
    payload: dict[str, Any],
) -> WorkflowTemplate:
    """Import a template from portable JSON."""
    user_id = _get_user(request)
    return import_template(payload, override_author=user_id)


@router.delete(
    "/marketplace/{template_id}",
    response={200: dict, 404: ErrorSchema},
    tags=["Templates"],
)
def delete_template(request, template_id: int) -> dict[str, Any]:
    """Delete a template."""
    template = get_object_or_404(WorkflowTemplate, id=template_id)
    template.delete()
    return {"status": "deleted", "template_id": template_id}
