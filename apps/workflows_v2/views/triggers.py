"""Trigger configuration views."""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.workflows_v2.models.trigger import WorkflowTrigger
from apps.workflows_v2.models.workflow import Workflow
from apps.workflows_v2.serializers import (
    ErrorSchema,
    TriggerCreateSchema,
    TriggerOutSchema,
    TriggerUpdateSchema,
)
from apps.workflows_v2.services.trigger_engine import (
    deactivate_trigger,
    evaluate_trigger,
    handle_webhook_trigger,
    register_trigger,
)

router = Router(auth=VoyagerKeycloakBearer())


def _get_tenant(request) -> str:
    """Extract tenant_id from request."""
    return getattr(request, "tenant_id", "") or getattr(request.auth, "tenant_id", "default")


def _get_user(request) -> str:
    """Extract user_id from request."""
    return getattr(request.auth, "sub", "anonymous")


@router.get("/{workflow_id}/triggers", response=list[TriggerOutSchema], tags=["Triggers"])
def list_triggers(request, workflow_id: int) -> list[WorkflowTrigger]:
    """List all triggers for a workflow."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    return list(workflow.triggers.order_by("-created_at"))


@router.post("/{workflow_id}/triggers", response=TriggerOutSchema, tags=["Triggers"])
def create_trigger(request, workflow_id: int, payload: TriggerCreateSchema) -> WorkflowTrigger:
    """Create a new trigger for a workflow."""
    tenant_id = _get_tenant(request)
    user_id = _get_user(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    return register_trigger(
        workflow_id=workflow.id,
        trigger_type=payload.trigger_type,
        name=payload.name,
        config=payload.config,
        created_by=user_id,
    )


@router.get(
    "/{workflow_id}/triggers/{trigger_id}",
    response=TriggerOutSchema,
    tags=["Triggers"],
)
def get_trigger(request, workflow_id: int, trigger_id: int) -> WorkflowTrigger:
    """Get a single trigger."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    return get_object_or_404(WorkflowTrigger, id=trigger_id, workflow=workflow)


@router.put(
    "/{workflow_id}/triggers/{trigger_id}",
    response=TriggerOutSchema,
    tags=["Triggers"],
)
def update_trigger(
    request,
    workflow_id: int,
    trigger_id: int,
    payload: TriggerUpdateSchema,
) -> WorkflowTrigger:
    """Update a trigger."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    trigger = get_object_or_404(WorkflowTrigger, id=trigger_id, workflow=workflow)

    if payload.name is not None:
        trigger.name = payload.name
    if payload.config is not None:
        trigger.config = payload.config
    if payload.is_active is not None:
        trigger.is_active = payload.is_active

    trigger.save(update_fields=["name", "config", "is_active", "updated_at"])
    return trigger


@router.delete(
    "/{workflow_id}/triggers/{trigger_id}",
    response={200: dict, 404: ErrorSchema},
    tags=["Triggers"],
)
def remove_trigger(request, workflow_id: int, trigger_id: int) -> dict[str, Any]:
    """Delete a trigger."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    trigger = get_object_or_404(WorkflowTrigger, id=trigger_id, workflow=workflow)
    trigger.delete()
    return {"status": "deleted", "trigger_id": trigger_id}


@router.post(
    "/{workflow_id}/triggers/{trigger_id}/deactivate",
    response=TriggerOutSchema,
    tags=["Triggers"],
)
def deactivate_trigger_view(request, workflow_id: int, trigger_id: int) -> WorkflowTrigger:
    """Deactivate a trigger."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    trigger = get_object_or_404(WorkflowTrigger, id=trigger_id, workflow=workflow)
    deactivate_trigger(trigger)
    return trigger


@router.post(
    "/{workflow_id}/triggers/{trigger_id}/test",
    response=dict,
    tags=["Triggers"],
)
def test_trigger(
    request,
    workflow_id: int,
    trigger_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Test a trigger against sample event data."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    trigger = get_object_or_404(WorkflowTrigger, id=trigger_id, workflow=workflow)
    event_data = payload.get("event_data", {})
    should_fire = evaluate_trigger(trigger, event_data)
    return {
        "trigger_id": trigger_id,
        "trigger_type": trigger.trigger_type,
        "should_fire": should_fire,
        "event_data": event_data,
    }


@router.post(
    "/{workflow_id}/triggers/{trigger_id}/webhook",
    auth=None,
    response=dict,
    tags=["Triggers"],
    include_in_schema=False,
)
def receive_webhook(
    request,
    workflow_id: int,
    trigger_id: int,
) -> dict[str, Any]:
    """Receive an inbound webhook for a trigger (public endpoint)."""
    workflow = get_object_or_404(Workflow, id=workflow_id)
    trigger = get_object_or_404(WorkflowTrigger, id=trigger_id, workflow=workflow)

    headers = dict(request.headers)
    body = request.body

    return handle_webhook_trigger(trigger, headers, body)
