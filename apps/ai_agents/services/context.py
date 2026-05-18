"""Context assembly service — brand, audience, performance, memory fusion."""

from __future__ import annotations

import logging
from typing import Any

from apps.ai_agents.models import AIAgent
from apps.ai_agents.models.context import AgentContext
from apps.ai_agents.services.memory import MemoryService

logger = logging.getLogger(__name__)


class ContextAssembler:
    """Service for assembling comprehensive agent context from multiple sources."""

    @staticmethod
    def assemble_context(
        agent_id: int,
        tenant_id: str,
        task_type: str,
        brand_data: dict[str, Any] | None = None,
        audience_data: list[dict[str, Any]] | None = None,
        performance_data: dict[str, Any] | None = None,
        current_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a comprehensive context payload for an agent.

        Combines brand guidelines, audience data, performance metrics,
        relevant memories, and current system state.

        Args:
            agent_id: Primary key of the agent.
            tenant_id: Tenant identifier.
            task_type: The type of task being executed.
            brand_data: Brand guidelines snapshot.
            audience_data: List of audience persona dicts.
            performance_data: Recent performance metrics.
            current_state: Active campaigns, scheduled content, approvals.

        Returns:
            Assembled context dictionary.
        """
        agent = AIAgent.objects.get(pk=agent_id, tenant_id=tenant_id)

        # 1. Brand context
        brand_context = ContextAssembler._build_brand_context(brand_data)

        # 2. Audience context
        audience_context = ContextAssembler._build_audience_context(audience_data)

        # 3. Performance context
        perf_context = ContextAssembler._build_performance_context(performance_data)

        # 4. Relevant memories
        memory_results = MemoryService.search_memory(agent_id, tenant_id, task_type, top_k=5)
        memory_ids = [m["qdrant_id"] for m in memory_results]
        memory_contents = [m["content"] for m in memory_results]

        # 5. Current state
        state = current_state or {}

        # 6. Task-specific context
        task_context = {}
        if task_type == "content_creation":
            task_context["seo_keywords"] = (brand_data or {}).get("seo_keywords", [])
            task_context["competitor_content"] = (brand_data or {}).get("competitor_content", [])

        # Token estimate (rough heuristic: 4 chars ~ 1 token)
        total_text = " ".join(memory_contents) + str(brand_context) + str(audience_context)
        token_estimate = len(total_text) // 4

        context = {
            "agent_id": str(agent.id),
            "agent_type": agent.agent_type,
            "task_type": task_type,
            "brand": brand_context,
            "audience": audience_context,
            "performance": perf_context,
            "memories": memory_contents,
            "current_state": state,
            "task_specific": task_context,
            "token_estimate": token_estimate,
        }

        # Persist context snapshot
        AgentContext.objects.create(
            agent=agent,
            tenant_id=tenant_id,
            task_type=task_type,
            brand_context=brand_context,
            audience_context=audience_context,
            performance_context=perf_context,
            memory_ids=memory_ids,
            current_state=state,
            token_estimate=token_estimate,
        )

        logger.info(
            "Assembled context for agent %s task=%s tokens=%d memories=%d",
            agent_id,
            task_type,
            token_estimate,
            len(memory_contents),
        )
        return context

    @staticmethod
    def get_recent_contexts(agent_id: int, tenant_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Retrieve recent context snapshots for an agent.

        Args:
            agent_id: Primary key of the agent.
            tenant_id: Tenant identifier.
            limit: Maximum number of contexts to return.

        Returns:
            List of context dicts.
        """
        contexts = AgentContext.objects.filter(
            agent_id=agent_id, tenant_id=tenant_id
        ).order_by("-assembled_at")[:limit]

        return [
            {
                "task_type": ctx.task_type,
                "brand_context": ctx.brand_context,
                "audience_context": ctx.audience_context,
                "performance_context": ctx.performance_context,
                "memory_ids": ctx.memory_ids,
                "current_state": ctx.current_state,
                "token_estimate": ctx.token_estimate,
                "assembled_at": ctx.assembled_at.isoformat(),
            }
            for ctx in contexts
        ]

    @staticmethod
    def _build_brand_context(brand_data: dict[str, Any] | None) -> dict[str, Any]:
        """Build brand context from available data.

        Args:
            brand_data: Raw brand data dict.

        Returns:
            Normalized brand context.
        """
        data = brand_data or {}
        return {
            "name": data.get("name", "Unknown Brand"),
            "tone": data.get("tone", "professional"),
            "colors": data.get("color_palette", []),
            "forbidden_words": data.get("forbidden_words", []),
            "competitors": data.get("competitor_list", []),
            "voice_guidelines": data.get("voice_guidelines", ""),
        }

    @staticmethod
    def _build_audience_context(audience_data: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        """Build audience context from persona data.

        Args:
            audience_data: List of persona dicts.

        Returns:
            Normalized audience context.
        """
        personas = audience_data or []
        return [
            {
                "name": p.get("name", f"Persona {i + 1}"),
                "demographics": p.get("demographics", {}),
                "preferences": p.get("content_preferences", {}),
                "channels": p.get("channel_preferences", []),
            }
            for i, p in enumerate(personas)
        ]

    @staticmethod
    def _build_performance_context(perf_data: dict[str, Any] | None) -> dict[str, Any]:
        """Build performance context from analytics data.

        Args:
            perf_data: Raw performance data.

        Returns:
            Normalized performance context.
        """
        data = perf_data or {}
        return {
            "top_content": data.get("top_content", []),
            "avg_engagement": data.get("avg_engagement", 0.0),
            "best_times": data.get("best_times", []),
            "best_formats": data.get("best_formats", []),
            "recent_campaigns": data.get("recent_campaigns", []),
        }
