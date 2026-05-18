"""Learning loop views — outcome analysis, strategy update, A/B testing."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from apps.ai_agents.models.learning import AgentLearningLoop
from apps.ai_agents.serializers import (
    ABTestConfigRequest,
    ABTestResultRequest,
    ABTestStatusResponse,
    OutcomeAnalysisRequest,
    OutcomeAnalysisResponse,
    UpdateStrategyRequest,
)
from apps.ai_agents.services.learning import LearningService


def analyze_outcomes(
    request: HttpRequest, agent_id: int, payload: OutcomeAnalysisRequest
) -> OutcomeAnalysisResponse:
    """Analyze recent task outcomes for an agent."""
    tenant_id = request.headers.get("X-Tenant-ID", "")
    result = LearningService.analyze_outcomes(
        agent_id=agent_id,
        tenant_id=tenant_id,
        period_days=payload.period_days,
    )
    return OutcomeAnalysisResponse(
        agent_id=result["agent_id"],
        tasks_analyzed=result["tasks_analyzed"],
        success_rate=result["success_rate"],
        success_patterns=result["success_patterns"],
        failure_patterns=result["failure_patterns"],
        avg_importance=result["avg_importance"],
    )


def update_strategy(
    request: HttpRequest, agent_id: int, payload: UpdateStrategyRequest
) -> AgentLearningLoop:
    """Update agent strategy based on outcome analysis."""
    tenant_id = request.headers.get("X-Tenant-ID", "")
    return LearningService.update_strategy(
        agent_id=agent_id,
        tenant_id=tenant_id,
        success_patterns=payload.success_patterns,
        failure_patterns=payload.failure_patterns,
        prompt_adjustments=payload.prompt_adjustments,
        ab_test_enabled=payload.ab_test_enabled,
        ab_test_config=payload.ab_test_config,
    )


def list_learning_loops(
    request: HttpRequest, agent_id: int, limit: int = 20
) -> list[AgentLearningLoop]:
    """List learning loop iterations for an agent."""
    return list(AgentLearningLoop.objects.filter(agent_id=agent_id).order_by("-applied_at")[:limit])


def configure_ab_test(
    request: HttpRequest, agent_id: int, payload: ABTestConfigRequest
) -> dict[str, Any]:
    """Configure an A/B test for an agent's strategy."""
    tenant_id = request.headers.get("X-Tenant-ID", "")
    return LearningService.configure_ab_test(
        agent_id=agent_id,
        tenant_id=tenant_id,
        control_config=payload.control_config,
        treatment_config=payload.treatment_config,
        traffic_split=payload.traffic_split,
    )


def record_ab_result(
    request: HttpRequest, agent_id: int, payload: ABTestResultRequest
) -> ABTestStatusResponse:
    """Record a result for an A/B test variant."""
    tenant_id = request.headers.get("X-Tenant-ID", "")
    result = LearningService.record_ab_result(
        agent_id=agent_id,
        tenant_id=tenant_id,
        variant=payload.variant,
        result=payload.result,
    )
    return ABTestStatusResponse(
        status=result.get("status", "error"),
        winner=result.get("winner", ""),
        control_rate=result.get("control_rate", 0.0),
        treatment_rate=result.get("treatment_rate", 0.0),
        control_samples=result.get("control_samples", 0),
        treatment_samples=result.get("treatment_samples", 0),
    )
