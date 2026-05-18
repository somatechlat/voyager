"""Agent orchestration service — lifecycle, creation, and execution."""

from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone

from apps.ai_agents.models import AIAgent
from apps.ai_agents.models.agent import AgentResourceLimit
from apps.ai_agents.services.resources import ResourceManager

logger = logging.getLogger(__name__)

# Default resource allocations per agent type
DEFAULT_RESOURCES: dict[str, dict[str, Any]] = {
    "creative": {"max_api_calls": 100, "max_memory_mb": 512, "max_cost_per_day": 5.00},
    "analyst": {"max_api_calls": 50, "max_memory_mb": 1024, "max_cost_per_day": 5.00},
    "optimizer": {"max_api_calls": 50, "max_memory_mb": 512, "max_cost_per_day": 5.00},
    "researcher": {"max_api_calls": 100, "max_memory_mb": 512, "max_cost_per_day": 5.00},
    "coordinator": {"max_api_calls": 200, "max_memory_mb": 256, "max_cost_per_day": 3.00},
}

# Default tools available per agent type
DEFAULT_TOOLS: dict[str, list[str]] = {
    "creative": ["text_generator", "image_prompt_builder", "ab_variant_creator"],
    "analyst": ["sql_query_runner", "chart_generator", "anomaly_detector"],
    "optimizer": ["ab_test_manager", "bid_adjuster", "audience_refiner"],
    "researcher": ["web_search", "data_aggregator", "report_generator"],
    "coordinator": ["task_router", "status_tracker", "conflict_resolver"],
}

# System prompt templates per agent type
SYSTEM_PROMPT_TEMPLATES: dict[str, str] = {
    "creative": (
        "You are a creative marketing agent. Generate engaging, on-brand content "
        "across multiple formats. Follow brand voice guidelines and optimize for "
        "audience engagement. Always respect content policies and resource limits."
    ),
    "analyst": (
        "You are a marketing analytics agent. Analyze campaign data, identify trends, "
        "detect anomalies, and generate actionable insights. Use SQL queries and "
        "statistical methods. Present findings clearly with visualizations."
    ),
    "optimizer": (
        "You are a campaign optimization agent. Manage A/B tests, adjust bidding "
        "strategies, and refine audience targeting. Focus on ROI improvement and "
        "efficient resource allocation."
    ),
    "researcher": (
        "You are a market research agent. Conduct competitive analysis, audience "
        "research, and trend monitoring. Aggregate data from multiple sources and "
        "produce comprehensive reports."
    ),
    "coordinator": (
        "You are a coordination agent. Route tasks to specialized agents, track "
        "execution status, resolve conflicts, and ensure collaboration protocols "
        "are followed. Prevent circular delegations."
    ),
}


class AgentOrchestrator:
    """Service for creating, configuring, and executing AI agents."""

    @staticmethod
    def create_agent(
        tenant_id: str,
        name: str,
        agent_type: str,
        model: str = "claude-3.5-sonnet",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        memory_enabled: bool = True,
        schedule: str = "",
        resources: dict[str, Any] | None = None,
    ) -> AIAgent:
        """Create and persist a new AI agent with type-specific defaults.

        Args:
            tenant_id: Tenant identifier for scoping.
            name: Human-readable agent name.
            agent_type: One of the five AIAgent.AgentType values.
            model: LLM model identifier.
            temperature: Sampling temperature (0.0 to 1.0).
            max_tokens: Maximum tokens per response.
            memory_enabled: Whether persistent memory is enabled.
            schedule: Optional cron expression.
            resources: Override resource allocations.

        Returns:
            The persisted AIAgent instance.
        """
        defaults = DEFAULT_RESOURCES.get(agent_type, DEFAULT_RESOURCES["creative"])
        user_resources = resources or {}

        config = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "system_prompt": SYSTEM_PROMPT_TEMPLATES.get(agent_type, ""),
            "tools": DEFAULT_TOOLS.get(agent_type, []),
            "memory_enabled": memory_enabled,
        }

        agent = AIAgent.objects.create(
            tenant_id=tenant_id,
            name=name,
            agent_type=agent_type,
            status=AIAgent.Status.IDLE,
            config=config,
            resources={
                "max_api_calls": user_resources.get("max_api_calls", defaults["max_api_calls"]),
                "max_memory_mb": user_resources.get("max_memory_mb", defaults["max_memory_mb"]),
                "max_cost_per_day": float(
                    user_resources.get("max_cost_per_day", defaults["max_cost_per_day"])
                ),
                "used_api_calls": 0,
                "used_memory_mb": 0,
                "used_cost_today": 0.0,
            },
            schedule=schedule,
        )

        AgentResourceLimit.objects.create(
            agent=agent,
            tenant_id=tenant_id,
            max_api_calls=user_resources.get("max_api_calls", defaults["max_api_calls"]),
            max_memory_mb=user_resources.get("max_memory_mb", defaults["max_memory_mb"]),
            max_cost_per_day=user_resources.get("max_cost_per_day", defaults["max_cost_per_day"]),
        )

        logger.info(
            "Created agent id=%s name=%s type=%s tenant=%s", agent.id, name, agent_type, tenant_id
        )
        return agent

    @staticmethod
    def run_agent(agent_id: int, task: dict[str, Any]) -> dict[str, Any]:
        """Execute a task on an agent after checking resource limits.

        Args:
            agent_id: Primary key of the agent.
            task: Task specification with keys like ``objective``, ``params``.

        Returns:
            Result dictionary with ``status``, ``output``, ``cost``.
        """
        try:
            agent = AIAgent.objects.get(pk=agent_id)
        except AIAgent.DoesNotExist:
            return {"status": "error", "error": "Agent not found"}

        resource_check = ResourceManager.check_resources(agent_id)
        if resource_check.get("action") == "suspended":
            agent.status = AIAgent.Status.SUSPENDED
            agent.save(update_fields=["status"])
            return {"status": "error", "error": f"Agent suspended: {resource_check['resource']}"}

        agent.status = AIAgent.Status.RUNNING
        agent.last_run_at = timezone.now()
        agent.save(update_fields=["status", "last_run_at"])

        result = {
            "status": "ok",
            "agent_id": str(agent.id),
            "agent_type": agent.agent_type,
            "task": task,
            "output": {},
            "api_calls": 1,
            "cost": 0.01,
        }

        ResourceManager.consume_resources(
            agent_id, api_calls=result["api_calls"], cost=result["cost"]
        )

        agent.status = AIAgent.Status.IDLE
        agent.save(update_fields=["status"])

        logger.info("Agent id=%s completed task status=%s", agent_id, result["status"])
        return result

    @staticmethod
    def list_agents(tenant_id: str, agent_type: str | None = None) -> list[AIAgent]:
        """List agents scoped to a tenant with optional type filter.

        Args:
            tenant_id: Tenant identifier.
            agent_type: Optional agent type filter.

        Returns:
            List of AIAgent instances.
        """
        qs = AIAgent.objects.filter(tenant_id=tenant_id)
        if agent_type:
            qs = qs.filter(agent_type=agent_type)
        return list(qs.order_by("-created_at"))

    @staticmethod
    def delete_agent(agent_id: int, tenant_id: str) -> bool:
        """Delete an agent and its associated data.

        Args:
            agent_id: Primary key of the agent.
            tenant_id: Tenant identifier for verification.

        Returns:
            True if deleted, False otherwise.
        """
        deleted, _ = AIAgent.objects.filter(pk=agent_id, tenant_id=tenant_id).delete()
        return deleted > 0
