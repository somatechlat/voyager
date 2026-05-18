"""Approval workflow views for content approval management."""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

from ..models import ApprovalWorkflow, ScheduledPost
from ..services.approval import (
    approve_step,
    check_timeouts,
    create_approval_instance,
    get_approval_status,
    get_pending_approvals,
    reject_approval,
    request_changes,
)

router = Router(auth=VoyagerKeycloakBearer())


class WorkflowIn:
    """Input for creating an approval workflow."""

    name: str
    type: str  # sequential, parallel, conditional
    steps: list[dict[str, Any]]
    auto_approve_on_timeout: bool = False


class WorkflowOut:
    """Output schema for workflow."""

    id: str
    name: str
    type: str
    steps: list[dict[str, Any]]
    auto_approve_on_timeout: bool
    is_active: bool
    created_at: str


class ApproveIn:
    """Input for approval action."""

    comment: str = ""


class RequestChangesIn:
    """Input for requesting changes."""

    comment: str


class InstanceOut:
    """Output schema for approval instance."""

    id: str
    workflow_id: str
    post_id: str
    current_step: int
    status: str
    step_started_at: str
    completed_at: str | None


@router.post("/workflows", response=WorkflowOut, tags=["Publishing Approval"])
def create_workflow(request, payload: WorkflowIn) -> dict[str, Any]:
    """Create an approval workflow."""
    tenant_id = getattr(request, "tenant_id", "default")
    user_id = getattr(request, "user_id", "anonymous")

    workflow = ApprovalWorkflow.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        type=payload.type,
        steps_json=payload.steps,
        auto_approve_on_timeout=payload.auto_approve_on_timeout,
        created_by=user_id,
    )
    return _workflow_to_dict(workflow)


@router.get("/workflows", response=list, tags=["Publishing Approval"])
def list_workflows(request) -> list[dict[str, Any]]:
    """List approval workflows."""
    tenant_id = getattr(request, "tenant_id", "default")
    workflows = ApprovalWorkflow.objects.filter(
        tenant_id=tenant_id,
        is_active=True,
    ).order_by("-created_at")
    return [_workflow_to_dict(w) for w in workflows]


@router.get("/workflows/{workflow_id}", response=WorkflowOut, tags=["Publishing Approval"])
def get_workflow(request, workflow_id: str) -> dict[str, Any]:
    """Get a workflow."""
    tenant_id = getattr(request, "tenant_id", "default")
    workflow = get_object_or_404(ApprovalWorkflow, id=workflow_id, tenant_id=tenant_id)
    return _workflow_to_dict(workflow)


@router.put("/workflows/{workflow_id}", response=WorkflowOut, tags=["Publishing Approval"])
def update_workflow(request, workflow_id: str, payload: WorkflowIn) -> dict[str, Any]:
    """Update a workflow."""
    tenant_id = getattr(request, "tenant_id", "default")
    workflow = get_object_or_404(ApprovalWorkflow, id=workflow_id, tenant_id=tenant_id)
    workflow.name = payload.name
    workflow.type = payload.type
    workflow.steps_json = payload.steps
    workflow.auto_approve_on_timeout = payload.auto_approve_on_timeout
    workflow.save(update_fields=["name", "type", "steps_json", "auto_approve_on_timeout"])
    return _workflow_to_dict(workflow)


@router.delete("/workflows/{workflow_id}", response={204: None}, tags=["Publishing Approval"])
def delete_workflow(request, workflow_id: str) -> tuple[int, None]:
    """Soft-delete a workflow."""
    tenant_id = getattr(request, "tenant_id", "default")
    workflow = get_object_or_404(ApprovalWorkflow, id=workflow_id, tenant_id=tenant_id)
    workflow.is_active = False
    workflow.save(update_fields=["is_active"])
    return 204, None


# ---- Approval Instances ----


@router.post("/posts/{post_id}/request-approval", response=dict, tags=["Publishing Approval"])
def request_approval(request, post_id: str) -> dict[str, Any]:
    """Request approval for a post."""
    tenant_id = getattr(request, "tenant_id", "default")
    post = get_object_or_404(ScheduledPost, id=post_id, tenant_id=tenant_id)

    if not post.approval_workflow_id:
        return {"success": False, "error": "No approval workflow configured"}

    try:
        instance = create_approval_instance(
            str(post.approval_workflow_id),
            str(post.id),
        )
        return {
            "success": True,
            "instance_id": str(instance.id),
            "workflow_id": str(instance.workflow_id),
            "status": instance.status,
            "current_step": instance.current_step,
        }
    except ValueError as exc:
        return {"success": False, "error": str(exc)}


@router.post("/approvals/{instance_id}/approve", response=dict, tags=["Publishing Approval"])
def do_approve(request, instance_id: str, payload: ApproveIn) -> dict[str, Any]:
    """Approve current step."""
    user_id = getattr(request, "user_id", "anonymous")
    return approve_step(instance_id, user_id, payload.comment)


@router.post("/approvals/{instance_id}/reject", response=dict, tags=["Publishing Approval"])
def do_reject(request, instance_id: str, payload: ApproveIn) -> dict[str, Any]:
    """Reject the approval."""
    user_id = getattr(request, "user_id", "anonymous")
    return reject_approval(instance_id, user_id, payload.comment)


@router.post(
    "/approvals/{instance_id}/request-changes", response=dict, tags=["Publishing Approval"]
)
def do_request_changes(request, instance_id: str, payload: RequestChangesIn) -> dict[str, Any]:
    """Request changes on current step."""
    user_id = getattr(request, "user_id", "anonymous")
    return request_changes(instance_id, user_id, payload.comment)


@router.get("/approvals/{instance_id}", response=dict, tags=["Publishing Approval"])
def get_instance(request, instance_id: str) -> dict[str, Any] | None:
    """Get approval instance status."""
    result = get_approval_status(instance_id)
    return result or {}


@router.get("/approvals/pending/list", response=list, tags=["Publishing Approval"])
def pending_approvals(request) -> list[dict[str, Any]]:
    """Get pending approvals for current user."""
    tenant_id = getattr(request, "tenant_id", "default")
    user_id = getattr(request, "user_id", "anonymous")
    return get_pending_approvals(tenant_id, user_id)


@router.post("/approvals/check-timeouts", response=dict, tags=["Publishing Approval"])
def check_approval_timeouts(request) -> dict[str, int]:
    """Check approval timeouts (admin/system endpoint)."""
    return check_timeouts()


def _workflow_to_dict(wf: ApprovalWorkflow) -> dict[str, Any]:
    return {
        "id": str(wf.id),
        "name": wf.name,
        "type": wf.type,
        "steps": list(wf.steps_json) if wf.steps_json else [],
        "auto_approve_on_timeout": wf.auto_approve_on_timeout,
        "is_active": wf.is_active,
        "created_at": wf.created_at.isoformat(),
    }
