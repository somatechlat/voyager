"""ApprovalWorkflow models — manages content approval chains.

Defines workflow templates, running instances, and per-step actions
for sequential, parallel, and conditional approval types.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from .base import TenantModel, TimeStampedModel, UUIDModel


class ApprovalWorkflow(UUIDModel, TimeStampedModel, TenantModel):
    """An approval workflow template.

    Attributes:
        name: Human-readable name.
        type: sequential, parallel, or conditional.
        steps_json: JSON array of step definitions.
        auto_approve_on_timeout: Auto-approve after 2x timeout.
    """

    class WorkflowType(models.TextChoices):
        SEQUENTIAL = "sequential", "Sequential"
        PARALLEL = "parallel", "Parallel"
        CONDITIONAL = "conditional", "Conditional"

    name = models.CharField(max_length=255, help_text="Workflow name")
    type = models.CharField(
        max_length=16, choices=WorkflowType.choices, help_text="Approval type",
    )
    steps_json = models.JSONField(
        default=list, help_text="Step definitions: [{step, name, approvers, timeoutHours, escalateTo, actions, condition}]",
    )
    auto_approve_on_timeout = models.BooleanField(
        default=False,
        help_text="Auto-approve after 2x step timeout",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.CharField(
        max_length=256, db_index=True, help_text="User UUID",
    )

    class Meta:
        db_table = "voyager_approval_workflow"
        verbose_name = "Approval Workflow"
        verbose_name_plural = "Approval Workflows"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.type})"

    def get_steps(self) -> list[dict]:
        """Return typed steps list."""
        return list(self.steps_json) if self.steps_json else []

    def step_count(self) -> int:
        """Return number of steps."""
        return len(self.get_steps())

    def get_step(self, step_number: int) -> dict | None:
        """Get step by number (1-indexed)."""
        steps = self.get_steps()
        for step in steps:
            if step.get("step") == step_number:
                return step
        return None


class ApprovalInstance(UUIDModel, TimeStampedModel):
    """A running approval instance.

    Attributes:
        workflow: FK to workflow template.
        scheduled_post: FK to scheduled post.
        current_step: Current step number (1-indexed).
        status: Pending, approved, rejected, expired.
        step_started_at: When current step started.
        completed_at: When instance was completed.
        escalated_at: When escalation happened.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"

    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.CASCADE,
        related_name="instances",
        db_index=True,
    )
    scheduled_post = models.OneToOneField(
        "ScheduledPost",
        on_delete=models.CASCADE,
        related_name="approval_instance",
        db_index=True,
    )
    current_step = models.PositiveIntegerField(
        default=1, help_text="Current step number (1-indexed)",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices,
        default=Status.PENDING, db_index=True,
    )
    step_started_at = models.DateTimeField(
        default=timezone.now,
        help_text="When current step started",
    )
    completed_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When instance was completed",
    )
    escalated_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When escalation happened",
    )

    class Meta:
        db_table = "voyager_approval_instance"
        verbose_name = "Approval Instance"
        verbose_name_plural = "Approval Instances"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workflow", "status"]),
            models.Index(fields=["scheduled_post", "status"]),
        ]

    def __str__(self) -> str:
        return f"Approval {self.scheduled_post_id} step={self.current_step} ({self.status})"

    def advance_step(self) -> bool:
        """Advance to next step. Returns False if no more steps."""
        steps = self.workflow.get_steps()
        if self.current_step >= len(steps):
            self.status = self.Status.APPROVED
            self.completed_at = timezone.now()
            self.save(update_fields=["status", "completed_at"])
            # Update scheduled post
            self.scheduled_post.approval_status = "approved"
            self.scheduled_post.status = "scheduled"
            self.scheduled_post.save(update_fields=["approval_status", "status"])
            return False
        self.current_step += 1
        self.step_started_at = timezone.now()
        self.escalated_at = None
        self.save(update_fields=["current_step", "step_started_at", "escalated_at"])
        return True

    def approve(self, approver_id: str, comment: str = "") -> None:
        """Approve current step and advance."""
        ApprovalAction.objects.create(
            instance=self,
            step=self.current_step,
            approver_id=approver_id,
            action=ApprovalAction.Action.APPROVE,
            comment=comment,
        )
        self.advance_step()

    def reject(self, approver_id: str, comment: str = "") -> None:
        """Reject the approval instance."""
        ApprovalAction.objects.create(
            instance=self,
            step=self.current_step,
            approver_id=approver_id,
            action=ApprovalAction.Action.REJECT,
            comment=comment,
        )
        self.status = self.Status.REJECTED
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])
        # Update scheduled post
        self.scheduled_post.approval_status = "rejected"
        self.scheduled_post.save(update_fields=["approval_status"])

    def request_changes(self, approver_id: str, comment: str = "") -> None:
        """Request changes on current step."""
        ApprovalAction.objects.create(
            instance=self,
            step=self.current_step,
            approver_id=approver_id,
            action=ApprovalAction.Action.REQUEST_CHANGES,
            comment=comment,
        )

    def is_overdue(self) -> bool:
        """Check if current step is overdue."""
        step = self.workflow.get_step(self.current_step)
        if not step:
            return False
        timeout_hours = step.get("timeoutHours")
        if not timeout_hours:
            return False
        deadline = self.step_started_at + timezone.timedelta(hours=timeout_hours)
        return timezone.now() > deadline

    def should_auto_approve(self) -> bool:
        """Check if 2x timeout has passed for auto-approval."""
        if not self.workflow.auto_approve_on_timeout:
            return False
        step = self.workflow.get_step(self.current_step)
        if not step:
            return False
        timeout_hours = step.get("timeoutHours")
        if not timeout_hours:
            return False
        deadline = self.step_started_at + timezone.timedelta(hours=timeout_hours * 2)
        return timezone.now() > deadline


class ApprovalAction(UUIDModel, TimeStampedModel):
    """A single approval action (approve, reject, request_changes).

    Attributes:
        instance: FK to approval instance.
        step: Step number this action applies to.
        approver_id: User UUID who took the action.
        action: approve, reject, or request_changes.
        comment: Optional comment.
    """

    class Action(models.TextChoices):
        APPROVE = "approve", "Approve"
        REJECT = "reject", "Reject"
        REQUEST_CHANGES = "request_changes", "Request Changes"

    instance = models.ForeignKey(
        ApprovalInstance,
        on_delete=models.CASCADE,
        related_name="actions",
        db_index=True,
    )
    step = models.PositiveIntegerField(help_text="Step number")
    approver_id = models.CharField(
        max_length=256, db_index=True, help_text="User UUID",
    )
    action = models.CharField(
        max_length=32, choices=Action.choices, db_index=True,
    )
    comment = models.TextField(blank=True)

    class Meta:
        db_table = "voyager_approval_action"
        verbose_name = "Approval Action"
        verbose_name_plural = "Approval Actions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["instance", "step"]),
            models.Index(fields=["approver_id", "action"]),
        ]

    def __str__(self) -> str:
        return f"Step {self.step} {self.action} by {self.approver_id[:8]}"
