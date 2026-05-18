"""Approval gate and approval request models."""

from __future__ import annotations

from django.db import models


class ApprovalGate(models.Model):
    """Configurable approval gate for high-risk operations.

    Defines conditions under which an operation requires approval,
    who can approve, escalation rules, and override policies.

    Attributes:
        id: Auto-incrementing primary key.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        name: Human-readable gate name.
        operations: List of operations this gate applies to.
        conditions: JSON conditions dict for when the gate triggers.
        approvers: JSON list of approver definitions (roles or users).
        require_all: Whether all approvers must approve.
        timeout_hours: Hours before auto-escalation.
        escalation: JSON escalation configuration.
        override_config: JSON override policy.
        enabled: Whether the gate is active.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128, db_index=True, help_text="Tenant identifier for multi-tenancy isolation"
    )
    name = models.CharField(max_length=255, help_text="Human-readable gate name")
    operations = models.JSONField(default=list, help_text="List of operations this gate applies to")
    conditions = models.JSONField(
        default=dict, blank=True, help_text="JSON conditions for when the gate triggers"
    )
    approvers = models.JSONField(
        default=list, help_text="JSON list of approver definitions (roles or users)"
    )
    require_all = models.BooleanField(
        default=True, help_text="Whether all approvers must approve (vs. any one)"
    )
    timeout_hours = models.IntegerField(default=48, help_text="Hours before auto-escalation")
    escalation = models.JSONField(
        default=dict, blank=True, help_text="JSON escalation configuration"
    )
    override_config = models.JSONField(
        default=dict, blank=True, help_text="JSON override policy configuration"
    )
    enabled = models.BooleanField(default=True, help_text="Whether the gate is active")
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="Timestamp when the record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, db_index=True, help_text="Timestamp when the record was last updated"
    )

    class Meta:
        db_table = "voyager_approval_gate"
        verbose_name = "Approval Gate"
        verbose_name_plural = "Approval Gates"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "enabled"]),
        ]

    def __str__(self) -> str:
        return self.name


class ApprovalRequest(models.Model):
    """Individual approval request against an ApprovalGate.

    Tracks the lifecycle of a single approval workflow: created,
    pending, approved, rejected, or escalated.

    Attributes:
        id: Auto-incrementing primary key.
        gate: The approval gate this request is for.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        requester_id: User ID who initiated the request.
        requester_email: Email of the requester.
        status: Current status of the request.
        approved_by: JSON list of user IDs who have approved.
        rejected_by: User ID of the rejecter (if rejected).
        justification: Reason text for the request.
        rejection_reason: Reason text for rejection.
        escalated_at: Timestamp when escalation occurred.
        escalated_to: User/role the request was escalated to.
        completed_at: Timestamp when the request was finalized.
        due_at: SLA deadline for approval.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    class Status(models.TextChoices):
        """Lifecycle status of an approval request."""

        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        ESCALATED = "escalated", "Escalated"
        OVERRIDDEN = "overridden", "Overridden"

    id = models.BigAutoField(primary_key=True, editable=False)
    gate = models.ForeignKey(
        ApprovalGate,
        on_delete=models.CASCADE,
        related_name="requests",
        help_text="The approval gate this request is for",
    )
    tenant_id = models.CharField(
        max_length=128, db_index=True, help_text="Tenant identifier for multi-tenancy isolation"
    )
    requester_id = models.CharField(max_length=256, help_text="User ID who initiated the request")
    requester_email = models.EmailField(
        max_length=255, blank=True, help_text="Email of the requester"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="Current status of the request",
    )
    approved_by = models.JSONField(
        default=list, help_text="JSON list of user IDs who have approved"
    )
    rejected_by = models.CharField(
        max_length=256, blank=True, help_text="User ID of the rejecter (if rejected)"
    )
    justification = models.TextField(blank=True, help_text="Reason text for the request")
    rejection_reason = models.TextField(blank=True, help_text="Reason text for rejection")
    escalated_at = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp when escalation occurred"
    )
    escalated_to = models.CharField(
        max_length=256, blank=True, help_text="User/role the request was escalated to"
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp when the request was finalized"
    )
    due_at = models.DateTimeField(help_text="SLA deadline for approval")
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="Timestamp when the record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, db_index=True, help_text="Timestamp when the record was last updated"
    )

    class Meta:
        db_table = "voyager_approval_request"
        verbose_name = "Approval Request"
        verbose_name_plural = "Approval Requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status", "due_at"]),
            models.Index(fields=["gate", "status"]),
            models.Index(fields=["requester_id", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Approval #{self.id} for {self.gate.name} ({self.status})"
