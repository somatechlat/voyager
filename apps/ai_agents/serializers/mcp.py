"""MCP tool schemas."""

from __future__ import annotations

from typing import Any

from ninja import Schema


class MCPToolSchema(Schema):
    """MCP tool definition."""

    tool_id: str
    name: str
    description: str
    version: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    endpoint: str
    rate_limit_max_calls: int
    rate_limit_window_seconds: int
    timeout_ms: int
    cost_per_call: float
    agent_id: int


class RegisterToolRequest(Schema):
    """Request body for registering a tool."""

    tool_id: str
    name: str
    description: str = ""
    version: str = "1.0.0"
    input_schema: dict[str, Any] = {}
    output_schema: dict[str, Any] = {}
    endpoint: str = ""
    rate_limit_max_calls: int = 100
    rate_limit_window_seconds: int = 3600
    timeout_ms: int = 30000
    cost_per_call: float = 0.01


class InvokeToolRequest(Schema):
    """Request body for invoking a tool."""

    params: dict[str, Any] = {}


class InvokeToolResponse(Schema):
    """Response for tool invocation."""

    status: str
    tool_id: str
    agent_id: str
    invocation_id: int
    cost: float
    error: str = ""


class ToolInvocationSchema(Schema):
    """Tool invocation log entry."""

    id: int
    tool_id: str
    agent_id: int
    invocation_input: dict[str, Any]
    invocation_output: dict[str, Any]
    success: bool | None
    error_message: str
    duration_ms: int | None
    cost: float
    called_at: str | None


class ToolInvocationListResponse(Schema):
    """Response for tool invocation history."""

    items: list[ToolInvocationSchema]
    total: int
