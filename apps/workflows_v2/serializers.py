"""Workflows v2 serializers — Ninja schemas for all API operations."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from ninja import Schema


# ── Workflow ────────────────────────────────────────────────────

class WorkflowCreateSchema(Schema):
    """Schema for creating a workflow."""

    name: str
    description: str = ""
    config: dict[str, Any] = {}
    trigger_config: dict[str, Any] = {}


class WorkflowUpdateSchema(Schema):
    """Schema for updating a workflow."""

    name: str | None = None
    description: str | None = None
    status: Literal["draft", "active", "paused", "archived"] | None = None
    config: dict[str, Any] | None = None
    trigger_config: dict[str, Any] | None = None


class WorkflowOutSchema(Schema):
    """Schema for workflow response."""

    id: int
    tenant_id: str
    name: str
    description: str
    version: int
    status: str
    nodes: list[dict[str, Any]]
    connections: list[dict[str, Any]]
    config: dict[str, Any]
    trigger_config: dict[str, Any]
    created_by: str
    created_at: datetime
    updated_at: datetime


class WorkflowListSchema(Schema):
    """Schema for workflow list item."""

    id: int
    name: str
    status: str
    version: int
    updated_at: datetime


# ── Workflow Nodes ──────────────────────────────────────────────

class NodeCreateSchema(Schema):
    """Schema for creating a node."""

    node_id: str
    node_type: str
    label: str = ""
    config: dict[str, Any] = {}
    position: dict[str, int] = {}


class NodeUpdateSchema(Schema):
    """Schema for updating a node."""

    label: str | None = None
    config: dict[str, Any] | None = None
    position: dict[str, int] | None = None


class NodeOutSchema(Schema):
    """Schema for node response."""

    id: int
    node_id: str
    node_type: str
    label: str
    config: dict[str, Any]
    position: dict[str, int]
    created_at: datetime


# ── Workflow Edges ──────────────────────────────────────────────

class EdgeCreateSchema(Schema):
    """Schema for creating an edge."""

    source: str
    target: str
    label: str = ""
    condition: str = ""


class EdgeUpdateSchema(Schema):
    """Schema for updating an edge."""

    label: str | None = None
    condition: str | None = None


class EdgeOutSchema(Schema):
    """Schema for edge response."""

    id: int
    source: str
    target: str
    label: str
    condition: str
    created_at: datetime


# ── Validation ──────────────────────────────────────────────────

class ValidationErrorSchema(Schema):
    """Schema for a single validation error."""

    type: str
    message: str
    node_id: str | None = None


class ValidationOutSchema(Schema):
    """Schema for workflow validation result."""

    valid: bool
    errors: list[ValidationErrorSchema]


# ── Simulation ──────────────────────────────────────────────────

class SimulateSchema(Schema):
    """Schema for simulation request."""

    test_data: dict[str, Any] = {}


class SimulationStepSchema(Schema):
    """Schema for a single simulation step."""

    nodeId: str
    nodeType: str
    input: dict[str, Any]
    output: dict[str, Any]
    duration: int
    decision: str | None = None
    status: str = "success"


class SimulateOutSchema(Schema):
    """Schema for simulation response."""

    simulationLog: list[SimulationStepSchema]
    finalContext: dict[str, Any]


# ── Versioning ──────────────────────────────────────────────────

class PublishVersionSchema(Schema):
    """Schema for publishing a version."""

    changelog: str = ""


class VersionOutSchema(Schema):
    """Schema for version response."""

    id: int
    workflow_id: int
    version: int
    changelog: str
    published_by: str
    created_at: datetime


class VersionDiffSchema(Schema):
    """Schema for version comparison result."""

    nodesAdded: list[dict[str, Any]]
    nodesRemoved: list[dict[str, Any]]
    nodesModified: list[dict[str, Any]]
    connectionsAdded: list[dict[str, Any]]
    connectionsRemoved: list[dict[str, Any]]


# ── Triggers ────────────────────────────────────────────────────

class TriggerCreateSchema(Schema):
    """Schema for creating a trigger."""

    trigger_type: str
    name: str
    config: dict[str, Any] = {}


class TriggerUpdateSchema(Schema):
    """Schema for updating a trigger."""

    name: str | None = None
    config: dict[str, Any] | None = None
    is_active: bool | None = None


class TriggerOutSchema(Schema):
    """Schema for trigger response."""

    id: int
    workflow_id: int
    trigger_type: str
    name: str
    config: dict[str, Any]
    is_active: bool
    last_triggered_at: datetime | None
    trigger_count: int
    created_by: str
    created_at: datetime


# ── Executions ──────────────────────────────────────────────────

class ExecutionOutSchema(Schema):
    """Schema for execution response."""

    id: int
    workflow_id: int
    version: int
    status: str
    trigger_type: str
    trigger_data: dict[str, Any]
    context: dict[str, Any]
    current_node: str
    progress: float
    started_at: datetime
    completed_at: datetime | None
    error: str


class ExecutionStartSchema(Schema):
    """Schema for starting an execution."""

    trigger_data: dict[str, Any] = {}


class ExecutionProgressSchema(Schema):
    """Schema for execution progress."""

    status: str
    progress: float
    current_node: str
    is_terminal: bool
    logs: list[dict[str, Any]]


# ── Human Approval ──────────────────────────────────────────────

class ApprovalDecisionSchema(Schema):
    """Schema for submitting an approval decision."""

    decision: Literal["approve", "reject", "request_changes"]
    feedback: str = ""
    form_data: dict[str, Any] = {}


class ApprovalOutSchema(Schema):
    """Schema for approval response."""

    id: int
    execution_id: int
    node_id: str
    approvers: list[str]
    current_approver: str
    timeout_hours: int
    status: str
    decision: str
    feedback: str
    form_data: dict[str, Any]
    submitted_at: datetime
    decided_at: datetime | None
    deadline_at: datetime | None


class ApprovalFormSchema(Schema):
    """Schema for rendered approval form."""

    approval_id: str
    title: str
    description: str
    fields: list[dict[str, Any]]
    decision_options: list[dict[str, Any]]
    can_escalate: bool
    escalate_to: str
    deadline: str | None


# ── Templates ───────────────────────────────────────────────────

class TemplateCreateSchema(Schema):
    """Schema for creating a template."""

    name: str
    description: str = ""
    category: str = "custom"
    workflow: dict[str, Any]
    configurable: list[dict[str, Any]] = []
    required_modules: list[str] = []
    tags: list[str] = []
    icon: str = ""


class TemplateInstallSchema(Schema):
    """Schema for installing a template."""

    customizations: dict[str, Any] = {}


class TemplateOutSchema(Schema):
    """Schema for template response."""

    id: int
    name: str
    description: str
    category: str
    tags: list[str]
    author: str
    version: str
    rating: float
    installs: int
    workflow: dict[str, Any]
    configurable: list[dict[str, Any]]
    required_modules: list[str]
    is_public: bool
    icon: str
    created_at: datetime


class TemplateListSchema(Schema):
    """Schema for template list item."""

    id: int
    name: str
    category: str
    author: str
    rating: float
    installs: int
    icon: str


# ── Webhook ─────────────────────────────────────────────────────

class WebhookInSchema(Schema):
    """Schema for inbound webhook payload."""

    payload: dict[str, Any] = {}


# ── Generic ─────────────────────────────────────────────────────

class StatusSchema(Schema):
    """Generic status response."""

    status: str
    detail: str = ""


class ErrorSchema(Schema):
    """Generic error response."""

    error: str
    detail: str = ""


class PaginatedListSchema(Schema):
    """Generic paginated list response."""

    count: int
    items: list[Any]
    page: int
    page_size: int
