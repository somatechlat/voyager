"""Resource management service — throttling, gradual degradation, suspension."""

from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone

from apps.ai_agents.models import AIAgent
from apps.ai_agents.models.agent import AgentResourceLimit

logger = logging.getLogger(__name__)

# Throttle thresholds
THROTTLE_LIGHT = 0.50
THROTTLE_MODERATE = 0.75
THROTTLE_CRITICAL = 0.90
SUSPEND_THRESHOLD = 1.00

# Throttle factors
FACTOR_FULL = 1.00
FACTOR_LIGHT = 0.75
FACTOR_MODERATE = 0.50
FACTOR_CRITICAL = 0.25
FACTOR_SUSPENDED = 0.00


class ResourceManager:
    """Service for monitoring and enforcing agent resource limits."""

    @staticmethod
    def check_resources(agent_id: int) -> dict[str, Any]:
        """Check resource utilization and apply throttling if needed.

        Args:
            agent_id: Primary key of the agent.

        Returns:
            Dict with action, resource, and throttle factor.
        """
        try:
            agent = AIAgent.objects.get(pk=agent_id)
            limits = AgentResourceLimit.objects.get(agent=agent)
        except (AIAgent.DoesNotExist, AgentResourceLimit.DoesNotExist):
            return {"action": "normal", "resource": None, "throttle_factor": 1.0}

        resources = [
            ("api_calls", limits.used_api_calls, limits.max_api_calls),
            ("memory", limits.used_memory_mb, limits.max_memory_mb),
            ("cost", float(limits.used_cost_today), float(limits.max_cost_per_day)),
        ]

        for resource_name, used, maximum in resources:
            if maximum <= 0:
                continue
            utilization = used / maximum

            if utilization >= SUSPEND_THRESHOLD:
                limits.throttle_factor = FACTOR_SUSPENDED
                limits.save(update_fields=["throttle_factor"])
                agent.status = AIAgent.Status.SUSPENDED
                agent.save(update_fields=["status"])
                logger.warning("Agent %s suspended: %s limit reached", agent_id, resource_name)
                return {"action": "suspended", "resource": resource_name, "throttle_factor": 0.0}

            elif utilization >= THROTTLE_CRITICAL:
                limits.throttle_factor = FACTOR_CRITICAL
                limits.save(update_fields=["throttle_factor"])
                logger.warning("Agent %s critically low on %s", agent_id, resource_name)
                return {
                    "action": "throttled_severe",
                    "resource": resource_name,
                    "throttle_factor": FACTOR_CRITICAL,
                }

            elif utilization >= THROTTLE_MODERATE:
                limits.throttle_factor = FACTOR_MODERATE
                limits.save(update_fields=["throttle_factor"])
                return {
                    "action": "throttled_moderate",
                    "resource": resource_name,
                    "throttle_factor": FACTOR_MODERATE,
                }

            elif utilization >= THROTTLE_LIGHT:
                limits.throttle_factor = FACTOR_LIGHT
                limits.save(update_fields=["throttle_factor"])
                return {
                    "action": "throttled_light",
                    "resource": resource_name,
                    "throttle_factor": FACTOR_LIGHT,
                }

        limits.throttle_factor = FACTOR_FULL
        limits.save(update_fields=["throttle_factor"])
        return {"action": "normal", "resource": None, "throttle_factor": FACTOR_FULL}

    @staticmethod
    def consume_resources(
        agent_id: int,
        api_calls: int = 0,
        memory_mb: int = 0,
        cost: float = 0.0,
    ) -> dict[str, Any]:
        """Increment resource usage counters.

        Args:
            agent_id: Primary key of the agent.
            api_calls: API calls to add.
            memory_mb: Memory to add.
            cost: Cost to add.

        Returns:
            Updated resource state dict.
        """
        try:
            limits = AgentResourceLimit.objects.get(agent_id=agent_id)
        except AgentResourceLimit.DoesNotExist:
            return {"status": "error", "error": "Resource limits not found"}

        limits.used_api_calls += api_calls
        limits.used_memory_mb += memory_mb
        limits.used_cost_today = float(limits.used_cost_today) + cost
        limits.save(update_fields=["used_api_calls", "used_memory_mb", "used_cost_today"])

        return {
            "used_api_calls": limits.used_api_calls,
            "used_memory_mb": limits.used_memory_mb,
            "used_cost_today": float(limits.used_cost_today),
            "max_api_calls": limits.max_api_calls,
            "max_memory_mb": limits.max_memory_mb,
            "max_cost_per_day": float(limits.max_cost_per_day),
        }

    @staticmethod
    def reset_daily_counters(tenant_id: str | None = None) -> dict[str, Any]:
        """Reset daily resource counters for all or a specific tenant.

        Args:
            tenant_id: Optional tenant filter.

        Returns:
            Dict with number of agents reset.
        """
        qs = AgentResourceLimit.objects.all()
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)

        count = qs.update(
            used_api_calls=0,
            used_memory_mb=0,
            used_cost_today=0.0000,
            throttle_factor=1.00,
            last_reset_at=timezone.now(),
        )

        # Reset agent statuses from suspended to idle
        AIAgent.objects.filter(status=AIAgent.Status.SUSPENDED).update(status=AIAgent.Status.IDLE)

        logger.info("Reset daily counters for %d agents", count)
        return {"reset_count": count}

    @staticmethod
    def get_resource_status(agent_id: int) -> dict[str, Any]:
        """Get current resource status for an agent.

        Args:
            agent_id: Primary key of the agent.

        Returns:
            Resource status dict.
        """
        try:
            limits = AgentResourceLimit.objects.select_related("agent").get(agent_id=agent_id)
        except AgentResourceLimit.DoesNotExist:
            return {"status": "error", "error": "Resource limits not found"}

        return {
            "agent_id": agent_id,
            "agent_name": limits.agent.name,
            "agent_status": limits.agent.status,
            "resources": {
                "api_calls": {
                    "used": limits.used_api_calls,
                    "max": limits.max_api_calls,
                    "utilization": (
                        round(limits.used_api_calls / limits.max_api_calls, 4)
                        if limits.max_api_calls > 0
                        else 0.0
                    ),
                },
                "memory": {
                    "used": limits.used_memory_mb,
                    "max": limits.max_memory_mb,
                    "utilization": (
                        round(limits.used_memory_mb / limits.max_memory_mb, 4)
                        if limits.max_memory_mb > 0
                        else 0.0
                    ),
                },
                "cost": {
                    "used": float(limits.used_cost_today),
                    "max": float(limits.max_cost_per_day),
                    "utilization": (
                        round(float(limits.used_cost_today) / float(limits.max_cost_per_day), 4)
                        if float(limits.max_cost_per_day) > 0
                        else 0.0
                    ),
                },
            },
            "throttle_factor": float(limits.throttle_factor),
            "last_reset_at": limits.last_reset_at.isoformat(),
        }
