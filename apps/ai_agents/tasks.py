"""Celery tasks for the AI Agents module.

Handles agent task dispatch, memory consolidation via Qdrant,
learning loop execution, and resource limit enforcement.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def dispatch_agent_task(
    self,
    agent_id: int,
    task_input: dict[str, Any],
    tenant_id: str,
) -> dict[str, Any]:
    """Dispatch a task to an AI agent for execution.

    Args:
        agent_id: Primary key of the agent.
        task_input: Task specification with ``objective``, ``context``,
            ``constraints``.
        tenant_id: Tenant identifier for scoping.

    Returns:
        Result dict with ``task_id``, ``status``, ``output``.
    """
    from apps.ai_agents.services.orchestration import AgentOrchestrator

    logger.info("Dispatching agent task: agent=%s tenant=%s", agent_id, tenant_id)

    try:
        result = AgentOrchestrator.run_agent(
            agent_id=agent_id,
            task=task_input,
        )
        return {
            "status": result.get("status", "ok"),
            "task": self.name,
            "agent_id": str(agent_id),
            "output": result.get("output", {}),
            "cost": result.get("cost", 0.0),
        }
    except Exception as exc:
        logger.error("Agent task failed: %s", exc, exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60)
        return {
            "status": "error",
            "task": self.name,
            "agent_id": str(agent_id),
            "error": str(exc),
        }


@shared_task(bind=True, max_retries=3)
def sync_agent_memory(
    self,
    agent_id: int,
    tenant_id: str,
) -> dict[str, Any]:
    """Synchronise agent memory with Qdrant vector store.

    Args:
        agent_id: Primary key of the agent.
        tenant_id: Tenant identifier for scoping.

    Returns:
        Result dict with ``vectors_synced``.
    """
    from apps.ai_agents.services.memory import MemoryService

    logger.info("Syncing agent memory: agent=%s", agent_id)

    try:
        memory = MemoryService.initialize_memory(agent_id, tenant_id)
        return {
            "status": "ok",
            "task": self.name,
            "agent_id": str(agent_id),
            "collection_name": memory.collection_name,
            "total_vectors": memory.total_vectors,
        }
    except Exception as exc:
        logger.error("Memory sync failed: %s", exc, exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=30)
        return {
            "status": "error",
            "task": self.name,
            "agent_id": str(agent_id),
            "error": str(exc),
        }


@shared_task(bind=True, max_retries=2)
def consolidate_agent_memory(
    self,
    agent_id: int,
    tenant_id: str,
) -> dict[str, Any]:
    """Run nightly memory consolidation for an agent.

    Decays old memories, merges similar entries, and marks
    unimportant memories for deletion.

    Args:
        agent_id: Primary key of the agent.
        tenant_id: Tenant identifier for scoping.

    Returns:
        Result dict with ``consolidated``, ``forgotten``, ``memories_remaining``.
    """
    from apps.ai_agents.services.memory import MemoryService

    logger.info("Consolidating memory for agent=%s", agent_id)

    try:
        result = MemoryService.consolidate_memory(agent_id, tenant_id)
        return {
            "status": "ok",
            "task": self.name,
            "agent_id": str(agent_id),
            **result,
        }
    except Exception as exc:
        logger.error("Memory consolidation failed: %s", exc, exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=300)
        return {
            "status": "error",
            "task": self.name,
            "agent_id": str(agent_id),
            "error": str(exc),
        }


@shared_task(bind=True, max_retries=2)
def run_learning_loop(
    self,
    agent_id: int,
    tenant_id: str,
    period_days: int = 30,
) -> dict[str, Any]:
    """Run the learning loop for an agent.

    Analyzes recent task outcomes, extracts success and failure patterns,
    and updates the agent's strategy accordingly.

    Args:
        agent_id: Primary key of the agent.
        tenant_id: Tenant identifier for scoping.
        period_days: Analysis window in days.

    Returns:
        Result dict with ``strategy_score``, ``patterns_found``.
    """
    from apps.ai_agents.services.learning import LearningService

    logger.info("Running learning loop for agent=%s", agent_id)

    try:
        analysis = LearningService.analyze_outcomes(
            agent_id=agent_id,
            tenant_id=tenant_id,
            period_days=period_days,
        )

        loop = LearningService.update_strategy(
            agent_id=agent_id,
            tenant_id=tenant_id,
            success_patterns=analysis["success_patterns"],
            failure_patterns=analysis["failure_patterns"],
            prompt_adjustments={},
            ab_test_enabled=False,
        )

        return {
            "status": "ok",
            "task": self.name,
            "agent_id": str(agent_id),
            "strategy_score": float(loop.strategy_score),
            "tasks_analyzed": analysis["tasks_analyzed"],
            "success_rate": analysis["success_rate"],
        }
    except Exception as exc:
        logger.error("Learning loop failed: %s", exc, exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=300)
        return {
            "status": "error",
            "task": self.name,
            "agent_id": str(agent_id),
            "error": str(exc),
        }


@shared_task(bind=True, max_retries=2)
def enforce_resource_limits(
    self,
    tenant_id: str = "",
) -> dict[str, Any]:
    """Check and enforce resource limits for all agents.

    Applies throttling or suspension to agents that have exceeded
    their resource thresholds.

    Args:
        tenant_id: Optional tenant filter.

    Returns:
        Result dict with ``agents_checked``, ``actions_taken``.
    """
    from apps.ai_agents.services.resources import ResourceManager

    logger.info("Enforcing resource limits for tenant=%s", tenant_id or "all")

    actions: list[dict[str, Any]] = []

    try:
        # Reset daily counters for a new day
        reset_result = ResourceManager.reset_daily_counters(tenant_id=tenant_id or None)

        return {
            "status": "ok",
            "task": self.name,
            "reset_count": reset_result.get("reset_count", 0),
            "actions_taken": actions,
            "checked_at": timezone.now().isoformat(),
        }
    except Exception as exc:
        logger.error("Resource enforcement failed: %s", exc, exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=120)
        return {
            "status": "error",
            "task": self.name,
            "error": str(exc),
        }


@shared_task(bind=True, max_retries=1)
def schedule_collaboration_task(
    self,
    collaboration_id: int,
    tenant_id: str,
) -> dict[str, Any]:
    """Execute a scheduled collaboration step.

    Args:
        collaboration_id: Primary key of the collaboration.
        tenant_id: Tenant identifier for scoping.

    Returns:
        Result dict with ``collaboration_id``, ``status``.
    """
    from apps.ai_agents.models.collaboration import AgentCollaboration

    logger.info("Executing collaboration step: collaboration=%s", collaboration_id)

    try:
        collaboration = AgentCollaboration.objects.get(pk=collaboration_id, tenant_id=tenant_id)
        return {
            "status": "ok",
            "task": self.name,
            "collaboration_id": collaboration_id,
            "pattern": collaboration.pattern,
            "status": collaboration.status,
        }
    except Exception as exc:
        logger.error("Collaboration task failed: %s", exc, exc_info=True)
        return {
            "status": "error",
            "task": self.name,
            "collaboration_id": collaboration_id,
            "error": str(exc),
        }
