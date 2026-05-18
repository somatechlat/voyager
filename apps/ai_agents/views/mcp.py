"""MCP tool views — registration, invocation, and history."""

from __future__ import annotations

from django.http import HttpRequest

from apps.ai_agents.models.mcp import MCPToolCall
from apps.ai_agents.serializers import (
    InvokeToolRequest,
    InvokeToolResponse,
    MCPToolSchema,
    RegisterToolRequest,
    ToolInvocationListResponse,
    ToolInvocationSchema,
)
from apps.ai_agents.services.mcp_tools import MCPToolService


def register_tool(request: HttpRequest, payload: RegisterToolRequest) -> MCPToolCall:
    """Register a new MCP tool for an agent."""
    tenant_id = request.headers.get("X-Tenant-ID", "")
    agent_id = request.GET.get("agent_id", "0")
    return MCPToolService.register_tool(
        tenant_id=tenant_id,
        agent_id=int(agent_id),
        tool_id=payload.tool_id,
        name=payload.name,
        description=payload.description,
        version=payload.version,
        input_schema=payload.input_schema,
        output_schema=payload.output_schema,
        endpoint=payload.endpoint,
        rate_limit_max_calls=payload.rate_limit_max_calls,
        rate_limit_window_seconds=payload.rate_limit_window_seconds,
        timeout_ms=payload.timeout_ms,
        cost_per_call=payload.cost_per_call,
    )


def list_tools(request: HttpRequest, agent_id: int = 0) -> list[MCPToolSchema]:
    """List registered MCP tools for a tenant."""
    tenant_id = request.headers.get("X-Tenant-ID", "")
    tools = MCPToolService.list_tools(
        tenant_id=tenant_id,
        agent_id=agent_id if agent_id > 0 else None,
    )
    return [
        MCPToolSchema(
            tool_id=t["tool_id"],
            name=t["name"],
            description=t["description"],
            version=t["version"],
            input_schema={},
            output_schema={},
            endpoint=t["endpoint"],
            rate_limit_max_calls=t["rate_limit_max_calls"],
            rate_limit_window_seconds=t["rate_limit_window_seconds"],
            timeout_ms=t["timeout_ms"],
            cost_per_call=t["cost_per_call"],
            agent_id=t["agent_id"],
        )
        for t in tools
    ]


def invoke_tool(
    request: HttpRequest,
    tool_id: str,
    agent_id: int,
    payload: InvokeToolRequest,
) -> InvokeToolResponse:
    """Invoke an MCP tool with schema validation and rate limiting."""
    tenant_id = request.headers.get("X-Tenant-ID", "")
    result = MCPToolService.invoke_tool(
        tenant_id=tenant_id,
        agent_id=agent_id,
        tool_id=tool_id,
        params=payload.params,
    )
    return InvokeToolResponse(
        status=result.get("status", "error"),
        tool_id=tool_id,
        agent_id=str(agent_id),
        invocation_id=result.get("invocation_id", 0),
        cost=result.get("cost", 0.0),
        error=result.get("error", ""),
    )


def get_invocations(
    request: HttpRequest,
    agent_id: int = 0,
    tool_id: str = "",
    limit: int = 50,
) -> ToolInvocationListResponse:
    """Get tool invocation history."""
    tenant_id = request.headers.get("X-Tenant-ID", "")
    invocations = MCPToolService.get_tool_invocations(
        tenant_id=tenant_id,
        agent_id=agent_id if agent_id > 0 else None,
        tool_id=tool_id or None,
        limit=limit,
    )
    return ToolInvocationListResponse(
        items=[
            ToolInvocationSchema(
                id=inv["id"],
                tool_id=inv["tool_id"],
                agent_id=inv["agent_id"],
                invocation_input=inv["invocation_input"],
                invocation_output=inv["invocation_output"],
                success=inv["success"],
                error_message=inv["error_message"],
                duration_ms=inv["duration_ms"],
                cost=inv["cost"],
                called_at=inv["called_at"],
            )
            for inv in invocations
        ],
        total=len(invocations),
    )
