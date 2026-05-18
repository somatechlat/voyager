"""Workflow template service — marketplace, import/export.

Manages workflow templates: publishing, discovery, installation,
and import/export of template definitions.
"""

from __future__ import annotations

import copy
import logging
from typing import Any

from apps.workflows_v2.models.template import WorkflowTemplate
from apps.workflows_v2.models.workflow import Workflow
from apps.workflows_v2.services.builder import validate_workflow

logger = logging.getLogger(__name__)


def publish_template(
    name: str,
    description: str,
    category: str,
    author: str,
    workflow_definition: dict[str, Any],
    configurable: list[dict[str, Any]] | None = None,
    required_modules: list[str] | None = None,
    tags: list[str] | None = None,
    icon: str = "",
) -> WorkflowTemplate:
    """Publish a workflow definition as a marketplace template.

    Args:
        name: Template name.
        description: Template description.
        category: Template category.
        author: Template author identifier.
        workflow_definition: The workflow definition JSON.
        configurable: List of configurable parameters.
        required_modules: List of required module names.
        tags: Searchable tags.
        icon: Icon identifier.

    Returns:
        The created WorkflowTemplate instance.

    Raises:
        ValueError: If the workflow definition is invalid.
    """
    # Validate workflow structure
    nodes = workflow_definition.get("nodes", [])
    connections = workflow_definition.get("connections", [])
    if not nodes:
        raise ValueError("Workflow must have at least one node")

    template = WorkflowTemplate.objects.create(
        name=name,
        description=description,
        category=category,
        author=author,
        workflow=workflow_definition,
        configurable=configurable or [],
        required_modules=required_modules or [],
        tags=tags or [],
        icon=icon,
    )
    logger.info("Published template %s: %s by %s", template.id, name, author)
    return template


def list_templates(
    category: str | None = None,
    search: str | None = None,
    is_public: bool | None = True,
) -> list[WorkflowTemplate]:
    """List available workflow templates.

    Args:
        category: Optional category filter.
        search: Optional search term for name/description.
        is_public: Filter by public visibility.

    Returns:
        List of WorkflowTemplate instances.
    """
    qs = WorkflowTemplate.objects.all()
    if is_public is not None:
        qs = qs.filter(is_public=is_public)
    if category:
        qs = qs.filter(category=category)
    if search:
        qs = qs.filter(
            django_models.Q(name__icontains=search)
            | django_models.Q(description__icontains=search)
            | django_models.Q(tags__contains=[search])
        )
    return list(qs)


def get_template_detail(template_id: int) -> WorkflowTemplate:
    """Get detailed template information.

    Args:
        template_id: The template ID.

    Returns:
        The WorkflowTemplate instance.

    Raises:
        WorkflowTemplate.DoesNotExist: If not found.
    """
    return WorkflowTemplate.objects.get(id=template_id)


def install_template(
    template: WorkflowTemplate,
    tenant_id: str,
    created_by: str,
    customizations: dict[str, Any] | None = None,
) -> Workflow:
    """Install a template as a new workflow for a tenant.

    Creates a new workflow from a template, applying any customizations
    to configurable parameters.

    Args:
        template: The template to install.
        tenant_id: The tenant ID.
        created_by: User ID installing the template.
        customizations: Custom parameter values.

    Returns:
        The created Workflow instance.
    """
    workflow_def = copy.deepcopy(template.workflow)

    # Apply customizations
    customizations = customizations or {}
    configurable = template.configurable or []
    for param in configurable:
        param_name = param.get("name", "")
        if param_name in customizations:
            _apply_customization(workflow_def, param_name, customizations[param_name], param)

    # Extract workflow properties
    name = workflow_def.get("name", template.name)
    description = workflow_def.get("description", template.description)
    nodes = workflow_def.get("nodes", [])
    connections = workflow_def.get("connections", [])
    config = workflow_def.get("config", {})
    trigger_config = workflow_def.get("trigger_config", {})

    workflow = Workflow.objects.create(
        tenant_id=tenant_id,
        name=name,
        description=description,
        status=Workflow.STATUS_DRAFT,
        nodes=nodes,
        connections=connections,
        config=config,
        trigger_config=trigger_config,
        created_by=created_by,
    )

    # Record the install
    template.record_install()

    logger.info(
        "Template %s installed as workflow %s for tenant %s",
        template.id,
        workflow.id,
        tenant_id,
    )
    return workflow


def _apply_customization(
    workflow_def: dict[str, Any],
    param_name: str,
    value: Any,
    param_schema: dict[str, Any],
) -> None:
    """Apply a customization value to a workflow definition.

    Args:
        workflow_def: The workflow definition to modify.
        param_name: The parameter name.
        value: The customized value.
        param_schema: The parameter schema with type info.
    """
    param_type = param_schema.get("type", "string")

    # Simple approach: scan all node configs and replace references
    for node in workflow_def.get("nodes", []):
        config = node.get("config", {})
        _replace_param_refs(config, param_name, value, param_type)


def _replace_param_refs(
    config: dict[str, Any],
    param_name: str,
    value: Any,
    param_type: str,
) -> None:
    """Recursively replace parameter references in a config dict.

    Replaces occurrences of ${param_name} with the actual value.
    """
    for key, val in config.items():
        if isinstance(val, str) and f"${{{param_name}}}" in val:
            if param_type == "string":
                config[key] = val.replace(f"${{{param_name}}}", str(value))
            else:
                config[key] = value
        elif isinstance(val, dict):
            _replace_param_refs(val, param_name, value, param_type)
        elif isinstance(val, list):
            for i, item in enumerate(val):
                if isinstance(item, str) and f"${{{param_name}}}" in item:
                    if param_type == "string":
                        val[i] = item.replace(f"${{{param_name}}}", str(value))
                    else:
                        val[i] = value
                elif isinstance(item, dict):
                    _replace_param_refs(item, param_name, value, param_type)


def export_template(template: WorkflowTemplate) -> dict[str, Any]:
    """Export a template to a portable JSON format.

    Args:
        template: The template to export.

    Returns:
        Dict with full template definition.
    """
    return {
        "templateId": f"tmpl_{template.id}",
        "name": template.name,
        "description": template.description,
        "category": template.category,
        "tags": template.tags,
        "author": template.author,
        "version": template.version,
        "rating": str(template.rating),
        "installs": template.installs,
        "workflow": template.workflow,
        "configurable": template.configurable,
        "required_modules": template.required_modules,
        "icon": template.icon,
    }


def import_template(
    data: dict[str, Any],
    override_author: str | None = None,
) -> WorkflowTemplate:
    """Import a template from a portable JSON format.

    Args:
        data: The template data dict.
        override_author: Optional author override.

    Returns:
        The created WorkflowTemplate instance.

    Raises:
        ValueError: If the data is missing required fields.
    """
    name = data.get("name")
    if not name:
        raise ValueError("Template name is required")

    workflow = data.get("workflow")
    if not workflow:
        raise ValueError("Workflow definition is required")

    template = WorkflowTemplate.objects.create(
        name=name,
        description=data.get("description", ""),
        category=data.get("category", WorkflowTemplate.CATEGORY_CUSTOM),
        tags=data.get("tags", []),
        author=override_author or data.get("author", "imported"),
        version=data.get("version", "1.0.0"),
        workflow=workflow,
        configurable=data.get("configurable", []),
        required_modules=data.get("required_modules", []),
        icon=data.get("icon", ""),
    )
    logger.info("Imported template %s: %s", template.id, name)
    return template


from django.db import models as django_models  # noqa: E402
