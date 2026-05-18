"""Learning service — outcome analysis, strategy adjustment, A/B testing."""

from __future__ import annotations

import logging
from typing import Any

from django.db.models import Avg, Q
from django.utils import timezone

from apps.ai_agents.models import AIAgent
from apps.ai_agents.models.learning import AgentLearningLoop

logger = logging.getLogger(__name__)


class LearningService:
    """Service for agent learning — outcome analysis and strategy improvement."""

    @staticmethod
    def analyze_outcomes(
        agent_id: int,
        tenant_id: str,
        period_days: int = 30,
    ) -> dict[str, Any]:
        """Analyze recent task outcomes to identify success and failure patterns.

        Args:
            agent_id: Primary key of the agent.
            tenant_id: Tenant identifier.
            period_days: Analysis window in days.

        Returns:
            Dict with success_patterns, failure_patterns, and statistics.
        """
        from apps.ai_agents.models.agent import AIAgent as AgentModel

        agent = AgentModel.objects.get(pk=agent_id, tenant_id=tenant_id)

        since = timezone.now() - timezone.timedelta(days=period_days)

        # Get tasks from memory entries as proxy for task history
        from apps.ai_agents.models.memory import MemoryEntry

        tasks = MemoryEntry.objects.filter(
            agent=agent,
            created_at__gte=since,
            metadata__has_key="success",
        )

        total = tasks.count()
        if total == 0:
            return {
                "agent_id": str(agent_id),
                "tasks_analyzed": 0,
                "success_patterns": [],
                "failure_patterns": [],
                "success_rate": 0.0,
            }

        successful = tasks.filter(metadata__success=True)
        failed = tasks.filter(Q(metadata__success=False) | Q(metadata__success=None))

        success_rate = successful.count() / total if total > 0 else 0.0

        # Extract patterns from metadata
        success_patterns = LearningService._extract_patterns(successful)
        failure_patterns = LearningService._extract_patterns(failed)

        result = {
            "agent_id": str(agent_id),
            "tasks_analyzed": total,
            "success_rate": round(success_rate, 4),
            "success_patterns": success_patterns,
            "failure_patterns": failure_patterns,
            "avg_importance": float(tasks.aggregate(avg=Avg("importance"))["avg"] or 0.0),
        }

        logger.info(
            "Analyzed %d tasks for agent %s: success_rate=%.2f",
            total,
            agent_id,
            success_rate,
        )
        return result

    @staticmethod
    def update_strategy(
        agent_id: int,
        tenant_id: str,
        success_patterns: list[dict[str, Any]],
        failure_patterns: list[dict[str, Any]],
        prompt_adjustments: dict[str, Any],
        ab_test_enabled: bool = False,
        ab_test_config: dict[str, Any] | None = None,
    ) -> AgentLearningLoop:
        """Update agent strategy based on outcome analysis.

        Args:
            agent_id: Primary key of the agent.
            tenant_id: Tenant identifier.
            success_patterns: Patterns from successful tasks.
            failure_patterns: Patterns from failed tasks.
            prompt_adjustments: System prompt changes to apply.
            ab_test_enabled: Whether to enable A/B testing.
            ab_test_config: A/B test configuration.

        Returns:
            The AgentLearningLoop record.
        """
        agent = AIAgent.objects.get(pk=agent_id, tenant_id=tenant_id)

        # Update agent config with prompt adjustments
        config = agent.config or {}
        if prompt_adjustments:
            current_prompt = config.get("system_prompt", "")
            additions = prompt_adjustments.get("additions", [])
            removals = prompt_adjustments.get("removals", [])

            for addition in additions:
                if addition not in current_prompt:
                    current_prompt += f"\n{addition}"

            for removal in removals:
                current_prompt = current_prompt.replace(removal, "")

            config["system_prompt"] = current_prompt.strip()
            agent.config = config
            agent.save(update_fields=["config"])

        # Calculate strategy score
        strategy_score = LearningService._calculate_strategy_score(
            success_patterns, failure_patterns
        )

        loop = AgentLearningLoop.objects.create(
            agent=agent,
            tenant_id=tenant_id,
            tasks_analyzed=len(success_patterns) + len(failure_patterns),
            success_patterns=success_patterns,
            failure_patterns=failure_patterns,
            prompt_adjustments=prompt_adjustments,
            ab_test_enabled=ab_test_enabled,
            ab_test_config=ab_test_config or {},
            strategy_score=strategy_score,
        )

        logger.info(
            "Updated strategy for agent %s: score=%.3f ab=%s",
            agent_id,
            strategy_score,
            ab_test_enabled,
        )
        return loop

    @staticmethod
    def configure_ab_test(
        agent_id: int,
        tenant_id: str,
        control_config: dict[str, Any],
        treatment_config: dict[str, Any],
        traffic_split: float = 0.5,
    ) -> dict[str, Any]:
        """Configure an A/B test for an agent's strategy.

        Args:
            agent_id: Primary key of the agent.
            tenant_id: Tenant identifier.
            control_config: Control variant configuration.
            treatment_config: Treatment variant configuration.
            traffic_split: Fraction of traffic to treatment (0.0 to 1.0).

        Returns:
            A/B test configuration dict.
        """
        agent = AIAgent.objects.get(pk=agent_id, tenant_id=tenant_id)

        ab_config = {
            "control": control_config,
            "treatment": treatment_config,
            "traffic_split": traffic_split,
            "started_at": timezone.now().isoformat(),
            "status": "running",
            "results": {"control": [], "treatment": []},
        }

        AgentLearningLoop.objects.create(
            agent=agent,
            tenant_id=tenant_id,
            ab_test_enabled=True,
            ab_test_config=ab_config,
            tasks_analyzed=0,
            strategy_score=0.5,
        )

        logger.info("A/B test configured for agent %s: split=%.2f", agent_id, traffic_split)
        return ab_config

    @staticmethod
    def record_ab_result(
        agent_id: int,
        tenant_id: str,
        variant: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """Record a result for an A/B test variant.

        Args:
            agent_id: Primary key of the agent.
            tenant_id: Tenant identifier.
            variant: "control" or "treatment".
            result: Result data dict.

        Returns:
            Updated A/B test state.
        """
        loop = (
            AgentLearningLoop.objects.filter(
                agent_id=agent_id, tenant_id=tenant_id, ab_test_enabled=True
            )
            .order_by("-applied_at")
            .first()
        )

        if not loop:
            return {"status": "error", "error": "No active A/B test found"}

        ab_config = dict(loop.ab_test_config)
        results = ab_config.get("results", {})
        variant_results = list(results.get(variant, []))
        variant_results.append({**result, "timestamp": timezone.now().isoformat()})
        results[variant] = variant_results
        ab_config["results"] = results

        loop.ab_test_config = ab_config
        loop.save(update_fields=["ab_test_config"])

        # Check if we have enough data to decide
        control_count = len(results.get("control", []))
        treatment_count = len(results.get("treatment", []))
        min_samples = ab_config.get("min_samples", 10)

        if control_count >= min_samples and treatment_count >= min_samples:
            return LearningService._evaluate_ab_test(ab_config)

        return {
            "status": "running",
            "control_samples": control_count,
            "treatment_samples": treatment_count,
        }

    @staticmethod
    def _extract_patterns(tasks_qs) -> list[dict[str, Any]]:
        """Extract patterns from a queryset of memory entries.

        Args:
            tasks_qs: QuerySet of MemoryEntry.

        Returns:
            List of pattern dicts.
        """
        patterns = []
        for entry in tasks_qs[:50]:
            meta = entry.metadata or {}
            patterns.append(
                {
                    "task_type": meta.get("task_type", "unknown"),
                    "content_preview": entry.content[:200],
                    "importance": float(entry.importance),
                    "source": meta.get("source", "unknown"),
                }
            )
        return patterns

    @staticmethod
    def _calculate_strategy_score(success_patterns: list, failure_patterns: list) -> float:
        """Calculate a strategy effectiveness score.

        Args:
            success_patterns: List of success pattern dicts.
            failure_patterns: List of failure pattern dicts.

        Returns:
            Score between 0.0 and 1.0.
        """
        total = len(success_patterns) + len(failure_patterns)
        if total == 0:
            return 0.5
        return min(max(len(success_patterns) / total, 0.0), 1.0)

    @staticmethod
    def _evaluate_ab_test(ab_config: dict[str, Any]) -> dict[str, Any]:
        """Evaluate A/B test results and declare a winner.

        Args:
            ab_config: A/B test configuration.

        Returns:
            Evaluation result dict.
        """
        results = ab_config.get("results", {})
        control_results = results.get("control", [])
        treatment_results = results.get("treatment", [])

        control_success = sum(1 for r in control_results if r.get("success"))
        treatment_success = sum(1 for r in treatment_results if r.get("success"))

        control_rate = control_success / len(control_results) if control_results else 0
        treatment_rate = treatment_success / len(treatment_results) if treatment_results else 0

        winner = "treatment" if treatment_rate > control_rate else "control"
        ab_config["status"] = "completed"
        ab_config["winner"] = winner
        ab_config["completed_at"] = timezone.now().isoformat()

        return {
            "status": "completed",
            "winner": winner,
            "control_rate": round(control_rate, 4),
            "treatment_rate": round(treatment_rate, 4),
            "control_samples": len(control_results),
            "treatment_samples": len(treatment_results),
        }
