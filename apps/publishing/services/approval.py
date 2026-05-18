"""Approval service — workflow engine for sequential/parallel/conditional approvals.

Handles workflow execution, timeout handling, escalation, and state
transitions for content approval chains.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.utils import timezone

from ..models import ApprovalInstance, ApprovalWorkflow, ScheduledPost

logger = logging.getLogger(__name__)


def create_approval_instance(
    workflow_id: str,
    scheduled_post_id: str,
) -> ApprovalInstance:
    """Create an approval instance for a scheduled post.

    Args:
        workflow_id: ApprovalWorkflow UUID.
        scheduled_post_id: ScheduledPost UUID.

    Returns:
        Created ApprovalInstance.

    Raises:
        ValueError: If workflow or post not found.
    """
    try:
        workflow = ApprovalWorkflow.objects.get(id=workflow_id)
    except ApprovalWorkflow.DoesNotExist:
        raise ValueError(f"Workflow {workflow_id} not found")

    try:
        post = ScheduledPost.objects.get(id=scheduled_post_id)
    except ScheduledPost.DoesNotExist:
        raise ValueError(f"Post {scheduled_post_id} not found")

    # Update post
    post.approval_workflow_id = workflow_id
    post.approval_status = ScheduledPost.ApprovalStatus.PENDING
    post.status = ScheduledPost.Status.PENDING_APPROVAL
    post.save(update_fields=["approval_workflow_id", "approval_status", "status"])

    instance = ApprovalInstance.objects.create(
        workflow=workflow,
        scheduled_post=post,
        current_step=1,
        status=ApprovalInstance.Status.PENDING,
        step_started_at=timezone.now(),
    )

    logger.info(
        "Approval instance %s created for post %s, workflow %s",
        instance.id,
        scheduled_post_id,
        workflow_id,
    )
    return instance


def approve_step(
    instance_id: str,
    approver_id: str,
    comment: str = "",
) -> dict[str, Any]:
    """Approve the current step and advance.

    Args:
        instance_id: ApprovalInstance UUID.
        approver_id: User UUID.
        comment: Optional comment.

    Returns:
        Result dict with status.
    """
    try:
        instance = ApprovalInstance.objects.select_related(
            "workflow",
            "scheduled_post",
        ).get(id=instance_id)
    except ApprovalInstance.DoesNotExist:
        return {"success": False, "error": "Approval instance not found"}

    if instance.status != instance.Status.PENDING:
        return {"success": False, "error": f"Instance is {instance.status}"}

    instance.approve(approver_id, comment)

    return {
        "success": True,
        "instance_id": str(instance.id),
        "current_step": instance.current_step,
        "status": instance.status,
    }


def reject_approval(
    instance_id: str,
    approver_id: str,
    comment: str = "",
) -> dict[str, Any]:
    """Reject the approval instance.

    Args:
        instance_id: ApprovalInstance UUID.
        approver_id: User UUID.
        comment: Optional comment.

    Returns:
        Result dict.
    """
    try:
        instance = ApprovalInstance.objects.select_related(
            "workflow",
            "scheduled_post",
        ).get(id=instance_id)
    except ApprovalInstance.DoesNotExist:
        return {"success": False, "error": "Approval instance not found"}

    if instance.status != instance.Status.PENDING:
        return {"success": False, "error": f"Instance is {instance.status}"}

    instance.reject(approver_id, comment)

    return {
        "success": True,
        "instance_id": str(instance.id),
        "status": instance.status,
    }


def request_changes(
    instance_id: str,
    approver_id: str,
    comment: str = "",
) -> dict[str, Any]:
    """Request changes on current step.

    Args:
        instance_id: ApprovalInstance UUID.
        approver_id: User UUID.
        comment: Required comment with change request.

    Returns:
        Result dict.
    """
    try:
        instance = ApprovalInstance.objects.select_related(
            "workflow",
            "scheduled_post",
        ).get(id=instance_id)
    except ApprovalInstance.DoesNotExist:
        return {"success": False, "error": "Approval instance not found"}

    if instance.status != instance.Status.PENDING:
        return {"success": False, "error": f"Instance is {instance.status}"}

    instance.request_changes(approver_id, comment)

    return {
        "success": True,
        "instance_id": str(instance.id),
        "current_step": instance.current_step,
        "status": instance.status,
    }


def check_timeouts() -> dict[str, int]:
    """Check all pending approval instances for timeouts.

    Escalates overdue approvals and auto-approves after 2x timeout.

    Returns:
        Dict with escalated and auto_approved counts.
    """
    instances = ApprovalInstance.objects.filter(
        status=ApprovalInstance.Status.PENDING,
    ).select_related("workflow", "scheduled_post")

    escalated = 0
    auto_approved = 0

    for instance in instances:
        try:
            step = instance.workflow.get_step(instance.current_step)
            if not step:
                continue

            timeout_hours = step.get("timeoutHours")
            if not timeout_hours:
                continue

            deadline = instance.step_started_at + timedelta(hours=timeout_hours)

            if timezone.now() > deadline and not instance.escalated_at:
                # Escalate
                escalate_to = step.get("escalateTo")
                if escalate_to:
                    instance.escalated_at = timezone.now()
                    instance.save(update_fields=["escalated_at"])
                    escalated += 1
                    logger.info(
                        "Approval %s step %s escalated to %s",
                        instance.id,
                        instance.current_step,
                        escalate_to,
                    )

            # Auto-approve after 2x timeout
            double_deadline = instance.step_started_at + timedelta(hours=timeout_hours * 2)
            if timezone.now() > double_deadline and instance.workflow.auto_approve_on_timeout:
                if instance.status == instance.Status.PENDING:
                    instance.approve("system", "Auto-approved due to timeout")
                    auto_approved += 1
                    logger.info("Approval %s auto-approved after timeout", instance.id)

        except Exception:
            logger.exception("Error checking timeout for instance %s", instance.id)

    return {"escalated": escalated, "auto_approved": auto_approved}


def get_approval_status(instance_id: str) -> dict[str, Any] | None:
    """Get detailed approval status.

    Args:
        instance_id: ApprovalInstance UUID.

    Returns:
        Status dict or None.
    """
    try:
        instance = (
            ApprovalInstance.objects.select_related(
                "workflow",
                "scheduled_post",
            )
            .prefetch_related("actions")
            .get(id=instance_id)
        )
    except ApprovalInstance.DoesNotExist:
        return None

    actions = list(instance.actions.all().order_by("step", "created_at"))
    steps = instance.workflow.get_steps()

    return {
        "instance_id": str(instance.id),
        "workflow_id": str(instance.workflow_id),
        "workflow_name": instance.workflow.name,
        "workflow_type": instance.workflow.type,
        "current_step": instance.current_step,
        "total_steps": len(steps),
        "status": instance.status,
        "step_started_at": instance.step_started_at.isoformat(),
        "completed_at": instance.completed_at.isoformat() if instance.completed_at else None,
        "escalated_at": instance.escalated_at.isoformat() if instance.escalated_at else None,
        "is_overdue": instance.is_overdue(),
        "actions": [
            {
                "step": a.step,
                "action": a.action,
                "approver_id": a.approver_id,
                "comment": a.comment,
                "created_at": a.created_at.isoformat(),
            }
            for a in actions
        ],
        "steps": steps,
    }


def get_pending_approvals(
    tenant_id: str,
    approver_id: str | None = None,
) -> list[dict[str, Any]]:
    """Get pending approvals for a tenant/approver.

    Args:
        tenant_id: Tenant scope.
        approver_id: Optional approver filter.

    Returns:
        List of pending approval dicts.
    """
    qs = (
        ApprovalInstance.objects.filter(
            status=ApprovalInstance.Status.PENDING,
            workflow__tenant_id=tenant_id,
        )
        .select_related("workflow", "scheduled_post")
        .order_by("-created_at")
    )

    results: list[dict[str, Any]] = []
    for instance in qs:
        step = instance.workflow.get_step(instance.current_step)
        approvers = step.get("approvers", []) if step else []
        # Filter by approver if specified
        if approver_id:
            if approver_id not in approvers and f"user:{approver_id}" not in approvers:
                continue
        results.append(
            {
                "instance_id": str(instance.id),
                "workflow_name": instance.workflow.name,
                "current_step": instance.current_step,
                "step_name": step.get("name", "") if step else "",
                "post_id": str(instance.scheduled_post_id),
                "post_caption": (
                    instance.scheduled_post.caption[:100] if instance.scheduled_post.caption else ""
                ),
                "approvers": approvers,
                "is_overdue": instance.is_overdue(),
                "step_started_at": instance.step_started_at.isoformat(),
            }
        )
    return results
