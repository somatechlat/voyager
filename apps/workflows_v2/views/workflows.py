"""Workflow CRUD and versioning views."""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.workflows_v2.models.workflow import Workflow, WorkflowVersion
from apps.workflows_v2.serializers import (
    WorkflowCreateSchema,
    WorkflowUpdateSchema,
    WorkflowOutSchema,
    WorkflowListSchema,
    PublishVersionSchema,
    VersionOutSchema,
    VersionDiffSchema,
    ValidationOutSchema,
    ErrorSchema,
)
from apps.workflows_v2.services.builder import (
    validate_workflow,
    simulate_workflow,
    publish_version,
    compare_versions,
)

router = Router(auth=VoyagerKeycloakBearer())


def _get_tenant(request) -> str:
    """Extract tenant_id from request."""
    return getattr(request, "tenant_id", "") or getattr(request.auth, "tenant_id", "default")


def _get_user(request) -> str:
    """Extract user_id from request."""
    return getattr(request.auth, "sub", "anonymous")


@router.get("", response=list[WorkflowListSchema], tags=["Workflows"])
def list_workflows(request) -> list[Workflow]:
    """List workflows for the current tenant."""
    tenant_id = _get_tenant(request)
    return list(
        Workflow.objects.filter(tenant_id=tenant_id).order_by("-updated_at")
    )


@router.post("", response=WorkflowOutSchema, tags=["Workflows"])
def create_workflow(request, payload: WorkflowCreateSchema) -> Workflow:
    """Create a new workflow."""
    tenant_id = _get_tenant(request)
    user_id = _get_user(request)
    workflow = Workflow.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        config=payload.config,
        trigger_config=payload.trigger_config,
        created_by=user_id,
    )
    return workflow


@router.get("/{workflow_id}", response=WorkflowOutSchema, tags=["Workflows"])
def get_workflow(request, workflow_id: int) -> Workflow:
    """Get a single workflow."""
    tenant_id = _get_tenant(request)
    return get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)


@router.put("/{workflow_id}", response=WorkflowOutSchema, tags=["Workflows"])
def update_workflow(
    request, workflow_id: int, payload: WorkflowUpdateSchema
) -> Workflow:
    """Update a workflow."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)

    if payload.name is not None:
        workflow.name = payload.name
    if payload.description is not None:
        workflow.description = payload.description
    if payload.status is not None:
        workflow.status = payload.status
    if payload.config is not None:
        workflow.config = payload.config
    if payload.trigger_config is not None:
        workflow.trigger_config = payload.trigger_config

    workflow.save(update_fields=["name", "description", "status", "config", "trigger_config", "updated_at"])
    return workflow


@router.delete("/{workflow_id}", response={200: dict, 404: ErrorSchema}, tags=["Workflows"])
def delete_workflow(request, workflow_id: int) -> dict[str, Any]:
    """Delete a workflow and all related data."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    workflow.delete()
    return {"status": "deleted", "workflow_id": workflow_id}


@router.post("/{workflow_id}/validate", response=ValidationOutSchema, tags=["Workflows"])
def validate_workflow_view(request, workflow_id: int) -> dict[str, Any]:
    """Validate a workflow definition."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    return validate_workflow(workflow)


@router.post("/{workflow_id}/simulate", response=dict, tags=["Workflows"])
def simulate_workflow_view(request, workflow_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Simulate a workflow with test data."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    test_data = payload.get("test_data", {})
    return simulate_workflow(workflow, test_data)


@router.post("/{workflow_id}/publish", response=VersionOutSchema, tags=["Workflows"])
def publish_version_view(
    request, workflow_id: int, payload: PublishVersionSchema
) -> WorkflowVersion:
    """Publish the current workflow as a new version."""
    tenant_id = _get_tenant(request)
    user_id = _get_user(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    return publish_version(workflow, user_id, payload.changelog)


@router.get("/{workflow_id}/versions", response=list[VersionOutSchema], tags=["Workflows"])
def list_versions(request, workflow_id: int) -> list[WorkflowVersion]:
    """List all versions of a workflow."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    return list(workflow.versions.order_by("-version"))


@router.get(
    "/{workflow_id}/versions/compare",
    response=VersionDiffSchema,
    tags=["Workflows"],
)
def compare_versions_view(
    request,
    workflow_id: int,
    version_a: int,
    version_b: int,
) -> dict[str, Any]:
    """Compare two workflow versions."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    v_a = get_object_or_404(WorkflowVersion, workflow=workflow, version=version_a)
    v_b = get_object_or_404(WorkflowVersion, workflow=workflow, version=version_b)
    return compare_versions(v_a, v_b)
