"""Learning loop schemas."""

from __future__ import annotations

from typing import Any

from ninja import Schema


class LearningLoopSchema(Schema):
    """Agent learning loop record."""

    id: int
    agent_id: int
    tenant_id: str
    tasks_analyzed: int
    success_patterns: list[dict[str, Any]]
    failure_patterns: list[dict[str, Any]]
    prompt_adjustments: dict[str, Any]
    ab_test_enabled: bool
    ab_test_config: dict[str, Any]
    strategy_score: float
    applied_at: str


class OutcomeAnalysisRequest(Schema):
    """Request body for outcome analysis."""

    period_days: int = 30


class OutcomeAnalysisResponse(Schema):
    """Response containing outcome analysis."""

    agent_id: str
    tasks_analyzed: int
    success_rate: float
    success_patterns: list[dict[str, Any]]
    failure_patterns: list[dict[str, Any]]
    avg_importance: float


class UpdateStrategyRequest(Schema):
    """Request body for updating strategy."""

    success_patterns: list[dict[str, Any]] = []
    failure_patterns: list[dict[str, Any]] = []
    prompt_adjustments: dict[str, Any] = {}
    ab_test_enabled: bool = False
    ab_test_config: dict[str, Any] | None = None


class ABTestConfigRequest(Schema):
    """Request body for configuring A/B test."""

    control_config: dict[str, Any] = {}
    treatment_config: dict[str, Any] = {}
    traffic_split: float = 0.5


class ABTestResultRequest(Schema):
    """Request body for recording A/B test result."""

    variant: str
    result: dict[str, Any] = {}


class ABTestStatusResponse(Schema):
    """Response for A/B test status."""

    status: str
    winner: str = ""
    control_rate: float = 0.0
    treatment_rate: float = 0.0
    control_samples: int = 0
    treatment_samples: int = 0
