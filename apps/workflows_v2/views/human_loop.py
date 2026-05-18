"""Human-in-the-loop approval views."""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.workflows_v2.models.workflow import Workflow
from apps.workflows_v2.models.execution import WorkflowExecution
from apps.workflows_v2.models.human_loop import HumanApprovalNode
from apps.workflows_v2.serializers import (
    ApprovalDecisionSchema,
    ApprovalOutSchema,
    ApprovalFormSchema,
    ErrorSchema,
)
from apps.workflows_v2.services.human_loop import (
    build_approval_context,
    render_approval_form,
    submit_approval_decision,
    escalate_approval,
    list_pending_approvals,
)

router = Router(auth=VoyagerKeycloakBearer())


def _get_tenant(request) -> str:
    """Extract tenant_id from request."""
    return getattr(request, "tenant_id", "") or getattr(request.auth, "tenant_id", "default")


def _get_user(request) -> str:
    """Extract user_id from request."""
    return getattr(request.auth, "sub", "anonymous")


@router.get(
    "/{workflow_id}/executions/{execution_id}/approvals",
    response=list[ApprovalOutSchema],
    tags=["Human Approval"],
)
def list_approvals(
    request,
    workflow_id: int,
    execution_id: int,
) -> list[HumanApprovalNode]:
    """List all approval requests for an execution."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    execution = get_object_or_404(
        WorkflowExecution, id=execution_id, workflow=workflow
    )
    return list(execution.approval_requests.order_by("-submitted_at"))


@router.get(
    "/{workflow_id}/executions/{execution_id}/approvals/{approval_id}",
    response=ApprovalOutSchema,
    tags=["Human Approval"],
)
def get_approval(
    request,
    workflow_id: int,
    execution_id: int,
    approval_id: int,
) -> HumanApprovalNode:
    """Get a single approval request."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    execution = get_object_or_404(
        WorkflowExecution, id=execution_id, workflow=workflow
    )
    return get_object_or_404(
        HumanApprovalNode, id=approval_id, execution=execution
    )


@router.get(
    "/{workflow_id}/executions/{execution_id}/approvals/{approval_id}/context",
    response=dict,
    tags=["Human Approval"],
)
def approval_context(
    request,
    workflow_id: int,
    execution_id: int,
    approval_id: int,
) -> dict[str, Any]:
    """Get the approval context for an approver."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    execution = get_object_or_404(
        WorkflowExecution, id=execution_id, workflow=workflow
    )
    approval = get_object_or_404(
        HumanApprovalNode, id=approval_id, execution=execution
    )
    triggered_by = execution.context.get("triggered_by")
    return build_approval_context(approval, workflow.name, triggered_by)


@router.get(
    "/{workflow_id}/executions/{execution_id}/approvals/{approval_id}/form",
    response=ApprovalFormSchema,
    tags=["Human Approval"],
)
def approval_form(
    request,
    workflow_id: int,
    execution_id: int,
    approval_id: int,
) -> dict[str, Any]:
    """Get the rendered approval form."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    execution = get_object_or_404(
        WorkflowExecution, id=execution_id, workflow=workflow
    )
    approval = get_object_or_404(
        HumanApprovalNode, id=approval_id, execution=execution
    )
    return render_approval_form(approval)


@router.post(
    "/{workflow_id}/executions/{execution_id}/approvals/{approval_id}/decide",
    response=ApprovalOutSchema,
    tags=["Human Approval"],
)
def submit_decision(
    request,
    workflow_id: int,
    execution_id: int,
    approval_id: int,
    payload: ApprovalDecisionSchema,
) -> HumanApprovalNode:
    """Submit an approval decision."""
    tenant_id = _get_tenant(request)
    user_id = _get_user(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    execution = get_object_or_404(
        WorkflowExecution, id=execution_id, workflow=workflow
    )
    approval = get_object_or_404(
        HumanApprovalNode, id=approval_id, execution=execution
    )
    return submit_approval_decision(
        approval=approval,
        decision=payload.decision,
        feedback=payload.feedback,
        form_data=payload.form_data,
        decided_by=user_id,
    )


@router.post(
    "/{workflow_id}/executions/{execution_id}/approvals/{approval_id}/escalate",
    response=ApprovalOutSchema,
    tags=["Human Approval"],
)
def escalate_approval_view(
    request,
    workflow_id: int,
    execution_id: int,
    approval_id: int,
) -> HumanApprovalNode:
    """Escalate a pending approval."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    execution = get_object_or_404(
        WorkflowExecution, id=execution_id, workflow=workflow
    )
    approval = get_object_or_404(
        HumanApprovalNode, id=approval_id, execution=execution
    )
    return escalate_approval(approval)


@router.get(
    "/approvals/pending",
    response=list[ApprovalOutSchema],
    tags=["Human Approval"],
)
def pending_approvals(request) -> list[HumanApprovalNode]:
    """List all pending approvals for the current user."""
    user_id = _get_user(request)
    return list_pending_approvals(approver=user_id)
