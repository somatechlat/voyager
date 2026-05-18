"""Human-in-the-loop service — approval nodes, form rendering, timeout.

Manages HITL approval lifecycle: creating requests, rendering forms,
processing decisions, handling timeouts, and escalation.
"""

from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone

from apps.workflows_v2.models.human_loop import HumanApprovalNode
from apps.workflows_v2.models.execution import WorkflowExecution

logger = logging.getLogger(__name__)


def create_approval_request(
    execution: WorkflowExecution,
    node_id: str,
    node_config: dict[str, Any],
    context: dict[str, Any],
) -> HumanApprovalNode:
    """Create a human approval request from a HITL node config.

    Args:
        execution: The parent workflow execution.
        node_id: The HITL node identifier.
        node_config: The node configuration JSON.
        context: Current execution context.

    Returns:
        The created HumanApprovalNode instance.
    """
    approvers = node_config.get("approvers", [])
    timeout_hours = node_config.get("timeoutHours", 24)
    form_config = node_config.get("form", {})
    escalate_to = node_config.get("escalateTo", "")

    deadline = timezone.now() + timezone.timedelta(hours=timeout_hours)

    approval = HumanApprovalNode.objects.create(
        execution=execution,
        node_id=node_id,
        approvers=approvers,
        current_approver=approvers[0] if approvers else "",
        form_config=form_config,
        timeout_hours=timeout_hours,
        escalate_to=escalate_to,
        deadline_at=deadline,
    )

    # Update execution status
    execution.status = WorkflowExecution.STATUS_WAITING_HITL
    execution.save(update_fields=["status"])

    logger.info(
        "Created approval request %s for execution %s node %s",
        approval.id,
        execution.id,
        node_id,
    )
    return approval


def build_approval_context(
    approval: HumanApprovalNode,
    workflow_name: str,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    """Build the context presented to an approver.

    Args:
        approval: The approval request.
        workflow_name: The name of the parent workflow.
        triggered_by: User ID who triggered the workflow.

    Returns:
        Dict with workflow context, content preview, decision options,
        form fields, and history.
    """
    form_config = approval.form_config
    fields = form_config.get("fields", [])

    context: dict[str, Any] = {
        "approval_id": str(approval.id),
        "workflow_name": workflow_name,
        "node_id": approval.node_id,
        "submitted_by": triggered_by,
        "submitted_at": approval.submitted_at.isoformat() if approval.submitted_at else None,
        "deadline_at": approval.deadline_at.isoformat() if approval.deadline_at else None,
        "status": approval.status,
        "feedback_required": any(f.get("required") for f in fields),
        "form_fields": fields,
        "options": [
            {"value": "approve", "label": "Approve", "color": "green"},
            {"value": "reject", "label": "Reject", "color": "red"},
            {"value": "request_changes", "label": "Request Changes", "color": "yellow"},
        ],
    }

    # Add execution context data if available
    exec_context = approval.execution.context
    if "content" in exec_context:
        context["content"] = exec_context["content"]
    elif "trigger" in exec_context:
        context["content"] = exec_context["trigger"]

    return context


def render_approval_form(approval: HumanApprovalNode) -> dict[str, Any]:
    """Render the approval form for a HITL node.

    Generates a structured form definition with field types,
    validation rules, and decision options.

    Args:
        approval: The approval request.

    Returns:
        Dict with form schema ready for frontend rendering.
    """
    form_config = approval.form_config
    fields = form_config.get("fields", [])

    rendered_fields: list[dict[str, Any]] = []
    for field in fields:
        rendered = {
            "name": field.get("name", ""),
            "type": field.get("type", "text"),
            "label": field.get("label", field.get("name", "").replace("_", " ").title()),
            "required": field.get("required", False),
            "placeholder": field.get("placeholder", ""),
            "options": field.get("options", []),
            "validation": field.get("validation", {}),
        }
        rendered_fields.append(rendered)

    return {
        "approval_id": str(approval.id),
        "title": f"Approval Required - {approval.node_id}",
        "description": "Please review and provide your decision.",
        "fields": rendered_fields,
        "decision_options": [
            {"value": "approve", "label": "Approve", "color": "green"},
            {"value": "reject", "label": "Reject", "color": "red"},
            {"value": "request_changes", "label": "Request Changes", "color": "yellow"},
        ],
        "can_escalate": bool(approval.escalate_to),
        "escalate_to": approval.escalate_to,
        "deadline": approval.deadline_at.isoformat() if approval.deadline_at else None,
    }


def submit_approval_decision(
    approval: HumanApprovalNode,
    decision: str,
    feedback: str = "",
    form_data: dict[str, Any] | None = None,
    decided_by: str = "",
) -> HumanApprovalNode:
    """Process an approval decision submission.

    Updates the approval status based on the decision and resumes
    the workflow execution if appropriate.

    Args:
        approval: The approval request.
        decision: The decision value ('approve', 'reject', etc.).
        feedback: Free-text feedback.
        form_data: Submitted form data.
        decided_by: User ID who made the decision.

    Returns:
        The updated HumanApprovalNode instance.

    Raises:
        ValueError: If the approval is already decided or decision is invalid.
    """
    if approval.is_decided():
        raise ValueError(f"Approval {approval.id} is already decided ({approval.status})")

    if decision not in ("approve", "reject", "request_changes"):
        raise ValueError(f"Invalid decision: {decision}")

    approval.decision = decision
    approval.feedback = feedback
    approval.form_data = form_data or {}
    approval.current_approver = decided_by

    if decision == "approve":
        approval.status = HumanApprovalNode.STATUS_APPROVED
    elif decision == "reject":
        approval.status = HumanApprovalNode.STATUS_REJECTED
    elif decision == "request_changes":
        approval.status = HumanApprovalNode.STATUS_REJECTED

    approval.decided_at = timezone.now()
    approval.save()

    # Update execution context with decision
    execution = approval.execution
    execution.context.setdefault("approvals", {})
    execution.context["approvals"][approval.node_id] = {
        "decision": decision,
        "feedback": feedback,
        "form_data": form_data,
        "decided_by": decided_by,
        "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
    }
    execution.status = WorkflowExecution.STATUS_RUNNING
    execution.save(update_fields=["context", "status"])

    logger.info(
        "Approval %s decided: %s by %s",
        approval.id,
        decision,
        decided_by,
    )
    return approval


def escalate_approval(approval: HumanApprovalNode) -> HumanApprovalNode:
    """Escalate a pending approval to the escalation target.

    Args:
        approval: The approval to escalate.

    Returns:
        The updated HumanApprovalNode instance.
    """
    if not approval.is_pending():
        return approval

    approval.status = HumanApprovalNode.STATUS_ESCALATED
    if approval.escalate_to:
        approval.current_approver = approval.escalate_to
    approval.save(update_fields=["status", "current_approver"])

    logger.info("Approval %s escalated to %s", approval.id, approval.escalate_to)
    return approval


def handle_timeout(approval: HumanApprovalNode) -> HumanApprovalNode:
    """Mark a pending approval as timed out.

    Args:
        approval: The approval that timed out.

    Returns:
        The updated HumanApprovalNode instance.
    """
    if not approval.is_pending():
        return approval

    approval.status = HumanApprovalNode.STATUS_TIMED_OUT
    approval.decided_at = timezone.now()
    approval.save(update_fields=["status", "decided_at"])

    # Update execution to mark it as failed or take fallback action
    execution = approval.execution
    execution.context.setdefault("approvals", {})
    execution.context["approvals"][approval.node_id] = {
        "decision": "timed_out",
        "reason": "Approval deadline exceeded",
    }
    execution.status = WorkflowExecution.STATUS_RUNNING
    execution.save(update_fields=["context", "status"])

    logger.info("Approval %s timed out", approval.id)
    return approval


def find_pending_timeouts() -> list[HumanApprovalNode]:
    """Find all approvals that have exceeded their deadline.

    Returns:
        List of HumanApprovalNode instances past their deadline.
    """
    now = timezone.now()
    return list(
        HumanApprovalNode.objects.filter(
            status=HumanApprovalNode.STATUS_PENDING,
            deadline_at__lt=now,
        ).select_related("execution")
    )


def list_pending_approvals(
    approver: str | None = None,
    execution_id: int | None = None,
) -> list[HumanApprovalNode]:
    """List pending approval requests.

    Args:
        approver: Filter by approver identifier.
        execution_id: Filter by execution ID.

    Returns:
        List of pending HumanApprovalNode instances.
    """
    qs = HumanApprovalNode.objects.filter(
        status=HumanApprovalNode.STATUS_PENDING,
    ).select_related("execution", "execution__workflow")

    if approver:
        qs = qs.filter(
            django_models.Q(approvers__contains=[approver])
            | django_models.Q(current_approver=approver)
        )
    if execution_id:
        qs = qs.filter(execution_id=execution_id)

    return list(qs)


from django.db import models as django_models  # noqa: E402
