"""Approval workflow service.

Manages approval gate configuration, approval request creation,
approval/rejection processing, and automatic escalation logic.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from apps.governance_v2.models import ApprovalGate, ApprovalRequest

logger = logging.getLogger(__name__)


class ApprovalService:
    """Service for approval workflow management.

    Creates approval requests against configured gates, processes
    approve/reject actions, handles escalation when requests timeout,
    and supports override with justification.
    """

    @staticmethod
    def create_approval_request(
        gate_id: int,
        tenant_id: str,
        requester_id: str,
        requester_email: str = "",
        justification: str = "",
    ) -> dict[str, Any]:
        """Create a new approval request against a gate.

        Args:
            gate_id: ID of the ApprovalGate to request against.
            tenant_id: Tenant identifier.
            requester_id: User ID of the person initiating the request.
            requester_email: Email of the requester.
            justification: Reason for the request.

        Returns:
            Dict with the created approval request details.
        """
        try:
            gate = ApprovalGate.objects.get(id=gate_id, tenant_id=tenant_id)
        except ApprovalGate.DoesNotExist:
            return {"error": f"ApprovalGate id={gate_id} not found for tenant {tenant_id}"}

        if not gate.enabled:
            return {"error": f"ApprovalGate id={gate_id} is disabled"}

        due_at = datetime.now(UTC) + timedelta(hours=gate.timeout_hours)

        req = ApprovalRequest.objects.create(
            gate=gate,
            tenant_id=tenant_id,
            requester_id=requester_id,
            requester_email=requester_email,
            status=ApprovalRequest.Status.PENDING,
            justification=justification,
            due_at=due_at,
        )

        logger.info(
            "Approval request created: id=%s gate=%s requester=%s",
            req.id,
            gate.name,
            requester_id,
        )

        return {
            "id": req.id,
            "gate_id": gate.id,
            "tenant_id": req.tenant_id,
            "requester_id": req.requester_id,
            "requester_email": req.requester_email,
            "status": req.status,
            "approved_by": req.approved_by,
            "justification": req.justification,
            "due_at": req.due_at,
            "created_at": req.created_at,
            "updated_at": req.updated_at,
        }

    @staticmethod
    def process_approval(
        request_id: int,
        approver_id: str,
        action: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Approve or reject an approval request.

        Args:
            request_id: ID of the ApprovalRequest.
            approver_id: User ID of the approver.
            action: Either 'approve' or 'reject'.
            reason: Optional reason for the action.

        Returns:
            Dict with the updated request details.
        """
        try:
            req = ApprovalRequest.objects.select_related("gate").get(id=request_id)
        except ApprovalRequest.DoesNotExist:
            return {"error": f"ApprovalRequest id={request_id} not found"}

        if req.status not in (ApprovalRequest.Status.PENDING, ApprovalRequest.Status.ESCALATED):
            return {"error": f"Request is already in status '{req.status}'"}

        now = datetime.now(UTC)

        if action == "approve":
            approved_list = list(req.approved_by or [])
            if approver_id not in approved_list:
                approved_list.append(approver_id)

            req.approved_by = approved_list
            req.updated_at = now

            # Check if all required approvers have approved
            gate = req.gate
            if gate.require_all:
                required_approvers = ApprovalService._get_required_approver_ids(
                    gate,
                )
                if set(approved_list) >= set(required_approvers):
                    req.status = ApprovalRequest.Status.APPROVED
                    req.completed_at = now
                    logger.info(
                        "Request %s fully approved by all required approvers",
                        request_id,
                    )
            else:
                # Any one approver is sufficient
                req.status = ApprovalRequest.Status.APPROVED
                req.completed_at = now
                logger.info("Request %s approved by %s", request_id, approver_id)

        elif action == "reject":
            req.status = ApprovalRequest.Status.REJECTED
            req.rejected_by = approver_id
            req.rejection_reason = reason
            req.completed_at = now
            logger.info(
                "Request %s rejected by %s: %s",
                request_id,
                approver_id,
                reason,
            )

        elif action == "override":
            override_config = req.gate.override_config or {}
            if not override_config.get("allowed", False):
                return {"error": "Override is not allowed for this gate"}

            min_length = override_config.get("min_justification_length", 20)
            if len(reason) < min_length:
                return {
                    "error": (
                        f"Override justification must be at least " f"{min_length} characters"
                    ),
                }

            req.status = ApprovalRequest.Status.OVERRIDDEN
            req.completed_at = now
            logger.info(
                "Request %s overridden by %s",
                request_id,
                approver_id,
            )

        else:
            return {"error": f"Unknown action: {action}"}

        req.save(
            update_fields=[
                "status",
                "approved_by",
                "rejected_by",
                "rejection_reason",
                "completed_at",
                "updated_at",
            ]
        )

        return {
            "id": req.id,
            "gate_id": req.gate.id,
            "tenant_id": req.tenant_id,
            "requester_id": req.requester_id,
            "status": req.status,
            "approved_by": req.approved_by,
            "rejected_by": req.rejected_by,
            "justification": req.justification,
            "rejection_reason": req.rejection_reason,
            "completed_at": req.completed_at,
            "due_at": req.due_at,
            "updated_at": req.updated_at,
        }

    @staticmethod
    def check_escalations(tenant_id: str) -> list[dict[str, Any]]:
        """Check for approval requests that need escalation.

        Finds pending requests past their escalation threshold.

        Args:
            tenant_id: Tenant identifier.

        Returns:
            List of escalated request dicts.
        """
        now = datetime.now(UTC)
        escalated: list[dict[str, Any]] = []

        pending = ApprovalRequest.objects.filter(
            tenant_id=tenant_id,
            status__in=[
                ApprovalRequest.Status.PENDING,
            ],
        ).select_related("gate")

        for req in pending:
            gate = req.gate
            escalation_config = gate.escalation or {}
            after_hours = escalation_config.get("after_hours", gate.timeout_hours / 2)
            escalation_threshold = req.created_at + timedelta(hours=after_hours)

            if now >= escalation_threshold and not req.escalated_at:
                escalate_to = escalation_config.get("escalate_to", "")
                req.status = ApprovalRequest.Status.ESCALATED
                req.escalated_at = now
                req.escalated_to = str(escalate_to)
                req.save(update_fields=["status", "escalated_at", "escalated_to"])

                logger.info(
                    "Request %s escalated to %s",
                    req.id,
                    escalate_to,
                )

                escalated.append(
                    {
                        "id": req.id,
                        "gate_id": gate.id,
                        "gate_name": gate.name,
                        "escalated_to": escalate_to,
                        "escalated_at": req.escalated_at,
                        "hours_pending": round(
                            (now - req.created_at).total_seconds() / 3600,
                            1,
                        ),
                    }
                )

        return escalated

    @staticmethod
    def get_overdue_requests(tenant_id: str) -> list[dict[str, Any]]:
        """Get approval requests past their due date.

        Args:
            tenant_id: Tenant identifier.

        Returns:
            List of overdue request dicts.
        """
        now = datetime.now(UTC)
        overdue = (
            ApprovalRequest.objects.filter(
                tenant_id=tenant_id,
                status__in=[
                    ApprovalRequest.Status.PENDING,
                    ApprovalRequest.Status.ESCALATED,
                ],
                due_at__lt=now,
            )
            .select_related("gate")
            .order_by("due_at")
        )

        return [
            {
                "id": req.id,
                "gate_id": req.gate.id,
                "gate_name": req.gate.name,
                "requester_id": req.requester_id,
                "due_at": req.due_at,
                "hours_overdue": round(
                    (now - req.due_at).total_seconds() / 3600,
                    1,
                ),
            }
            for req in overdue
        ]

    @staticmethod
    def _get_required_approver_ids(gate: ApprovalGate) -> list[str]:
        """Extract approver IDs from a gate's approver configuration.

        Args:
            gate: ApprovalGate instance.

        Returns:
            List of approver identifier strings.
        """
        approvers = gate.approvers or []
        ids: list[str] = []
        for approver in approvers:
            if isinstance(approver, dict):
                approver_type = approver.get("type", "")
                value = approver.get("value", "")
                ids.append(f"{approver_type}:{value}")
            elif isinstance(approver, str):
                ids.append(approver)
        return ids
