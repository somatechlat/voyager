"""Multi-agent collaboration service — delegation, 5 patterns, circular prevention."""

from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone

from apps.ai_agents.models import AIAgent
from apps.ai_agents.models.collaboration import AgentCollaboration

logger = logging.getLogger(__name__)

MAX_DELEGATION_DEPTH = 5


class CollaborationService:
    """Service for multi-agent collaboration with delegation and pattern orchestration."""

    @staticmethod
    def create_collaboration(
        tenant_id: str,
        initiator_agent_id: int,
        task_id: str,
        pattern: str,
        max_depth: int = MAX_DELEGATION_DEPTH,
    ) -> AgentCollaboration:
        """Create a new collaboration session.

        Args:
            tenant_id: Tenant identifier.
            initiator_agent_id: Primary key of the initiating agent.
            task_id: Task identifier.
            pattern: One of AgentCollaboration.Pattern values.
            max_depth: Maximum delegation depth.

        Returns:
            The AgentCollaboration instance.
        """
        initiator = AIAgent.objects.get(pk=initiator_agent_id, tenant_id=tenant_id)
        collaboration = AgentCollaboration.objects.create(
            tenant_id=tenant_id,
            initiator_agent=initiator,
            task_id=task_id,
            pattern=pattern,
            status=AgentCollaboration.Status.PENDING,
            delegation_chain=[str(initiator_agent_id)],
            max_depth=max_depth,
            messages=[],
        )
        logger.info(
            "Created collaboration id=%s pattern=%s task=%s",
            collaboration.id,
            pattern,
            task_id,
        )
        return collaboration

    @staticmethod
    def delegate_task(
        tenant_id: str,
        collaboration_id: int,
        from_agent_id: int,
        to_agent_id: int,
        task: dict[str, Any],
    ) -> dict[str, Any]:
        """Delegate a task with circular delegation prevention.

        Args:
            tenant_id: Tenant identifier.
            collaboration_id: Collaboration session ID.
            from_agent_id: Delegating agent ID.
            to_agent_id: Target agent ID.
            task: Task specification.

        Returns:
            Result dict with status and any error.
        """
        try:
            collaboration = AgentCollaboration.objects.get(pk=collaboration_id, tenant_id=tenant_id)
        except AgentCollaboration.DoesNotExist:
            return {"status": "error", "error": "Collaboration not found"}

        chain = list(collaboration.delegation_chain)

        # Check for circular delegation
        to_agent_str = str(to_agent_id)
        if to_agent_str in chain:
            error_msg = f"Circular delegation detected: chain={chain + [to_agent_str]}"
            logger.warning(error_msg)
            collaboration.messages.append(
                {
                    "type": "error",
                    "timestamp": timezone.now().isoformat(),
                    "error": "circular_delegation",
                    "chain": chain + [to_agent_str],
                }
            )
            collaboration.status = AgentCollaboration.Status.FAILED
            collaboration.save(update_fields=["messages", "status"])
            return {
                "status": "error",
                "error": "circular_delegation",
                "chain": chain + [to_agent_str],
            }

        # Check max depth
        if len(chain) >= collaboration.max_depth:
            error_msg = f"Max delegation depth exceeded: {len(chain)} >= {collaboration.max_depth}"
            logger.warning(error_msg)
            collaboration.messages.append(
                {
                    "type": "error",
                    "timestamp": timezone.now().isoformat(),
                    "error": "max_depth_exceeded",
                }
            )
            collaboration.save(update_fields=["messages"])
            return {"status": "error", "error": "max_delegation_depth_exceeded"}

        # Check both agents exist
        try:
            from_agent = AIAgent.objects.get(pk=from_agent_id, tenant_id=tenant_id)
            to_agent = AIAgent.objects.get(pk=to_agent_id, tenant_id=tenant_id)
        except AIAgent.DoesNotExist:
            return {"status": "error", "error": "Agent not found"}

        # Update chain and status
        chain.append(to_agent_str)
        collaboration.delegation_chain = chain
        collaboration.status = AgentCollaboration.Status.ACTIVE
        if not collaboration.started_at:
            collaboration.started_at = timezone.now()

        collaboration.messages.append(
            {
                "type": "task_delegation",
                "timestamp": timezone.now().isoformat(),
                "from": str(from_agent_id),
                "to": str(to_agent_id),
                "task_id": collaboration.task_id,
                "task": task,
            }
        )
        collaboration.save(update_fields=["delegation_chain", "status", "started_at", "messages"])

        logger.info(
            "Delegated task from agent %s to agent %s in collaboration %s",
            from_agent_id,
            to_agent_id,
            collaboration_id,
        )

        # Execute the task on the target agent
        result = CollaborationService._execute_delegated_task(to_agent, task)

        # Log result
        collaboration.messages.append(
            {
                "type": "delegation_result",
                "timestamp": timezone.now().isoformat(),
                "from": str(from_agent_id),
                "to": str(to_agent_id),
                "task_id": collaboration.task_id,
                "result": result,
            }
        )
        collaboration.save(update_fields=["messages"])

        return {"status": "ok", "result": result, "chain": chain}

    @staticmethod
    def complete_collaboration(
        tenant_id: str,
        collaboration_id: int,
        result_summary: dict[str, Any],
    ) -> dict[str, Any]:
        """Mark a collaboration as completed.

        Args:
            tenant_id: Tenant identifier.
            collaboration_id: Collaboration session ID.
            result_summary: JSON summary of the outcome.

        Returns:
            Dict with completion status.
        """
        updated = AgentCollaboration.objects.filter(
            pk=collaboration_id, tenant_id=tenant_id
        ).update(
            status=AgentCollaboration.Status.COMPLETED,
            completed_at=timezone.now(),
            result_summary=result_summary,
        )
        if updated:
            logger.info("Collaboration %s completed", collaboration_id)
            return {"status": "ok", "completed": True}
        return {"status": "error", "error": "Collaboration not found"}

    @staticmethod
    def get_collaboration_messages(tenant_id: str, collaboration_id: int) -> list[dict[str, Any]]:
        """Retrieve the message log for a collaboration.

        Args:
            tenant_id: Tenant identifier.
            collaboration_id: Collaboration session ID.

        Returns:
            List of message dicts.
        """
        try:
            collab = AgentCollaboration.objects.get(pk=collaboration_id, tenant_id=tenant_id)
            return list(collab.messages)
        except AgentCollaboration.DoesNotExist:
            return []

    @staticmethod
    def list_active_collaborations(tenant_id: str) -> list[dict[str, Any]]:
        """List active collaborations for a tenant.

        Args:
            tenant_id: Tenant identifier.

        Returns:
            List of collaboration dicts.
        """
        collaborations = AgentCollaboration.objects.filter(
            tenant_id=tenant_id, status=AgentCollaboration.Status.ACTIVE
        ).order_by("-created_at")

        return [
            {
                "id": c.id,
                "task_id": c.task_id,
                "pattern": c.pattern,
                "status": c.status,
                "initiator_agent_id": c.initiator_agent_id,
                "delegation_chain": c.delegation_chain,
                "started_at": c.started_at.isoformat() if c.started_at else None,
            }
            for c in collaborations
        ]

    @staticmethod
    def _execute_delegated_task(agent: AIAgent, task: dict[str, Any]) -> dict[str, Any]:
        """Execute a delegated task on the target agent.

        Args:
            agent: The target AIAgent.
            task: Task specification.

        Returns:
            Task execution result.
        """
        return {
            "status": "ok",
            "agent_id": str(agent.id),
            "agent_type": agent.agent_type,
            "task": task,
            "output": {},
        }
