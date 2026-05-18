"""OKR serializers — SP-005 schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from ninja import Schema


class ObjectiveIn(Schema):
    """Input for creating/updating objective."""
    title: str
    level: str
    owner_id: str
    quarter: str
    description: str = ""
    parent_id: str | None = None
    team_id: str | None = None


class ObjectiveOut(Schema):
    """Output for an objective."""
    id: str
    title: str
    level: str
    quarter: str
    status: str
    progress: Decimal
    description: str
    team_id: str | None
    owner_id: str
    parent_id: str | None
    created_at: datetime
    updated_at: datetime


class KeyResultIn(Schema):
    """Input for creating/updating key result."""
    title: str
    kr_type: str
    target_value: float
    start_value: float = 0
    current_value: float = 0
    direction: str = "increase"
    unit: str = ""
    data_source: dict[str, Any] | None = None


class KeyResultOut(Schema):
    """Output for a key result."""
    id: str
    objective_id: str
    title: str
    kr_type: str
    target_value: Decimal
    current_value: Decimal
    start_value: Decimal
    direction: str
    unit: str
    progress: Decimal
    confidence: str
    data_source: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ProgressUpdateIn(Schema):
    """Input for updating key result progress."""
    current_value: float


class ProgressOut(Schema):
    """Output for progress calculation."""
    progress: float
    progressPercent: float
    currentValue: float
    targetValue: float
    confidence: str
    velocity: float
    projectedCompletion: float
    objective_progress: float | None = None
    objective_status: str | None = None


class ObjectiveTreeOut(Schema):
    """Output for objective tree with nested children and KRs."""
    id: str
    title: str
    level: str
    quarter: str
    status: str
    progress: Decimal
    description: str
    team_id: str | None
    owner_id: str
    key_results: list[dict[str, Any]]
    children: list[dict[str, Any]]
    depth: int


class OKRFilter(Schema):
    """Query filters for OKR listing."""
    quarter: str | None = None
    level: str | None = None
    status: str | None = None
    owner_id: str | None = None
    limit: int = 20
    offset: int = 0


class ConfidenceSummaryOut(Schema):
    """Output for OKR confidence summary."""
    objectives_by_status: dict[str, int]
    total_objectives: int
    average_progress: float
