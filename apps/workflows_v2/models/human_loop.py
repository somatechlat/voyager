"""HumanApprovalNode model — human-in-the-loop approval tracking."""

from __future__ import annotations

from django.db import models


class HumanApprovalNode(models.Model):
    """A human approval request created by a HITL node during execution.

    Tracks the approval lifecycle: pending, approved, rejected, timed_out,
    or escalated. Includes form rendering config and timeout handling.

    Attributes:
        id: Auto-incrementing primary key.
        execution: The parent workflow execution.
        node_id: The HITL node identifier.
        approvers: JSON list of approver identifiers.
        current_approver: The currently assigned approver.
        form_config: JSON form field definitions.
        timeout_hours: Hours before auto-timeout.
        status: Approval status.
        decision: The final decision value.
        feedback: Free-text feedback from approver.
        form_data: Submitted form data JSON.
        escalated_to: Escalation target if timeout.
        submitted_at: When approval was requested.
        decided_at: When decision was made.
        deadline_at: Timeout deadline.
    """

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_TIMED_OUT = "timed_out"
    STATUS_ESCALATED = "escalated"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_TIMED_OUT, "Timed Out"),
        (STATUS_ESCALATED, "Escalated"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    id = models.BigAutoField(primary_key=True, editable=False)
    execution = models.ForeignKey(
        "WorkflowExecution",
        on_delete=models.CASCADE,
        related_name="approval_requests",
        help_text="The parent workflow execution",
    )
    node_id = models.CharField(
        max_length=100,
        help_text="The HITL node identifier",
    )
    approvers = models.JSONField(
        default=list,
        help_text="List of approver identifiers (user IDs or roles)",
    )
    current_approver = models.CharField(
        max_length=256,
        blank=True,
        help_text="Currently assigned approver",
    )
    form_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Form field definitions for the approval UI",
    )
    timeout_hours = models.PositiveIntegerField(
        default=24,
        help_text="Hours before auto-timeout",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    decision = models.CharField(
        max_length=50,
        blank=True,
        help_text="The final decision value (e.g. 'approve', 'reject')",
    )
    feedback = models.TextField(
        blank=True,
        help_text="Free-text feedback from approver",
    )
    form_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Submitted form data",
    )
    escalate_to = models.CharField(
        max_length=256,
        blank=True,
        help_text="Escalation target if timeout",
    )
    submitted_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )
    decided_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    deadline_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timeout deadline",
    )

    class Meta:
        db_table = "voyager_human_approval_node"
        verbose_name = "Human Approval Node"
        verbose_name_plural = "Human Approval Nodes"
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["execution", "node_id"]),
            models.Index(fields=["status", "deadline_at"]),
            models.Index(fields=["current_approver", "status"]),
        ]

    def __str__(self) -> str:
        return f"Approval {self.node_id} ({self.status})"

    def is_decided(self) -> bool:
        """Check if a decision has been made (terminal state)."""
        return self.status in (
            self.STATUS_APPROVED,
            self.STATUS_REJECTED,
            self.STATUS_TIMED_OUT,
            self.STATUS_CANCELLED,
        )

    def is_pending(self) -> bool:
        """Check if approval is still pending."""
        return self.status == self.STATUS_PENDING
