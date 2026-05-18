"""Automation Sequence schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ninja import Schema


class AutomationSequenceCreateSchema(Schema):
    """Schema for creating an automation sequence."""

    tenant_id: str
    name: str
    trigger_type: str = "list_signup"
    trigger_config: dict[str, Any] = {}
    steps: list[dict[str, Any]] = []
    entry_criteria: dict[str, Any] = {}
    exit_criteria: dict[str, Any] = {}
    frequency_cap: int = 0


class AutomationSequenceUpdateSchema(Schema):
    """Schema for updating an automation sequence."""

    name: str | None = None
    trigger_type: str | None = None
    trigger_config: dict[str, Any] | None = None
    steps: list[dict[str, Any]] | None = None
    status: str | None = None
    entry_criteria: dict[str, Any] | None = None
    exit_criteria: dict[str, Any] | None = None
    frequency_cap: int | None = None


class AutomationSequenceListSchema(Schema):
    """Schema for sequence list responses."""

    id: int
    tenant_id: str
    name: str
    trigger_type: str
    status: str
    total_enrolled: int
    total_completed: int
    step_count: int
    created_at: datetime


class AutomationSequenceDetailSchema(Schema):
    """Schema for detailed sequence responses."""

    id: int
    tenant_id: str
    name: str
    trigger_type: str
    trigger_config: dict[str, Any]
    steps: list[dict[str, Any]]
    status: str
    total_enrolled: int
    total_completed: int
    total_exited: int
    completion_rate: float
    entry_criteria: dict[str, Any]
    exit_criteria: dict[str, Any]
    frequency_cap: int
    created_at: datetime
    updated_at: datetime


class AutomationTriggerSchema(Schema):
    """Schema for testing a trigger."""

    subscriber_id: int
    event_data: dict[str, Any] = {}


class SequenceEvaluateSchema(Schema):
    """Schema for evaluating a sequence step."""

    subscriber_id: int
    step_id: str
    event_data: dict[str, Any] = {}
