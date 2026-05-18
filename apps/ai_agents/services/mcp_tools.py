"""MCP tool service — registration, schema validation, rate limiting, invocation."""

from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone

from apps.ai_agents.models import AIAgent
from apps.ai_agents.models.mcp import MCPToolCall

logger = logging.getLogger(__name__)


class MCPToolService:
    """Service for MCP tool registration, discovery, and invocation."""

    @staticmethod
    def register_tool(
        tenant_id: str,
        agent_id: int,
        tool_id: str,
        name: str,
        description: str,
        version: str,
        input_schema: dict[str, Any],
        output_schema: dict[str, Any],
        endpoint: str,
        rate_limit_max_calls: int = 100,
        rate_limit_window_seconds: int = 3600,
        timeout_ms: int = 30000,
        cost_per_call: float = 0.01,
    ) -> MCPToolCall:
        """Register a new tool for an agent.

        Args:
            tenant_id: Tenant identifier.
            agent_id: Primary key of the owning agent.
            tool_id: Unique tool identifier.
            name: Human-readable name.
            description: Tool description.
            version: Semantic version.
            input_schema: JSON Schema for inputs.
            output_schema: JSON Schema for outputs.
            endpoint: Invocation endpoint.
            rate_limit_max_calls: Rate limit max calls.
            rate_limit_window_seconds: Rate limit window.
            timeout_ms: Timeout in milliseconds.
            cost_per_call: Cost per call in dollars.

        Returns:
            The MCPToolCall registration record.
        """
        agent = AIAgent.objects.get(pk=agent_id, tenant_id=tenant_id)

        tool, _ = MCPToolCall.objects.update_or_create(
            agent=agent,
            tenant_id=tenant_id,
            tool_id=tool_id,
            defaults={
                "name": name,
                "description": description,
                "version": version,
                "input_schema": input_schema,
                "output_schema": output_schema,
                "endpoint": endpoint,
                "rate_limit_max_calls": rate_limit_max_calls,
                "rate_limit_window_seconds": rate_limit_window_seconds,
                "timeout_ms": timeout_ms,
                "cost_per_call": cost_per_call,
            },
        )
        logger.info("Registered tool %s for agent %s", tool_id, agent_id)
        return tool

    @staticmethod
    def invoke_tool(
        tenant_id: str,
        agent_id: int,
        tool_id: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Invoke a tool with schema validation and rate limiting.

        Args:
            tenant_id: Tenant identifier.
            agent_id: Primary key of the invoking agent.
            tool_id: Tool to invoke.
            params: Input parameters.

        Returns:
            Invocation result dict.
        """
        try:
            agent = AIAgent.objects.get(pk=agent_id, tenant_id=tenant_id)
            tool = MCPToolCall.objects.get(agent=agent, tool_id=tool_id, tenant_id=tenant_id)
        except (AIAgent.DoesNotExist, MCPToolCall.DoesNotExist):
            return {"status": "error", "error": "Tool or agent not found"}

        # Validate input against schema
        validation = MCPToolService._validate_schema(params, tool.input_schema)
        if not validation["valid"]:
            return {"status": "error", "error": "invalid_input", "details": validation["errors"]}

        # Check rate limit
        recent_calls = MCPToolService._count_recent_calls(
            agent_id, tool_id, tool.rate_limit_window_seconds
        )
        if recent_calls >= tool.rate_limit_max_calls:
            return {
                "status": "error",
                "error": "rate_limit_exceeded",
                "retry_after": tool.rate_limit_window_seconds,
            }

        # Record invocation
        invocation = MCPToolCall.objects.create(
            agent=agent,
            tenant_id=tenant_id,
            tool_id=tool_id,
            name=tool.name,
            description=tool.description,
            version=tool.version,
            input_schema=tool.input_schema,
            output_schema=tool.output_schema,
            endpoint=tool.endpoint,
            rate_limit_max_calls=tool.rate_limit_max_calls,
            rate_limit_window_seconds=tool.rate_limit_window_seconds,
            timeout_ms=tool.timeout_ms,
            cost_per_call=tool.cost_per_call,
            invocation_input=params,
            success=True,
            called_at=timezone.now(),
        )

        logger.info("Tool %s invoked by agent %s", tool_id, agent_id)

        return {
            "status": "ok",
            "tool_id": tool_id,
            "agent_id": str(agent_id),
            "invocation_id": invocation.id,
            "cost": float(tool.cost_per_call),
        }

    @staticmethod
    def list_tools(tenant_id: str, agent_id: int | None = None) -> list[dict[str, Any]]:
        """List registered tools for a tenant.

        Args:
            tenant_id: Tenant identifier.
            agent_id: Optional agent filter.

        Returns:
            List of tool dicts.
        """
        qs = MCPToolCall.objects.filter(tenant_id=tenant_id, success__isnull=True)
        if agent_id:
            qs = qs.filter(agent_id=agent_id)

        tools = qs.values(
            "tool_id",
            "name",
            "description",
            "version",
            "endpoint",
            "rate_limit_max_calls",
            "rate_limit_window_seconds",
            "timeout_ms",
            "cost_per_call",
            "agent_id",
        ).distinct()

        return list(tools)

    @staticmethod
    def get_tool_invocations(
        tenant_id: str,
        agent_id: int | None = None,
        tool_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get invocation history.

        Args:
            tenant_id: Tenant identifier.
            agent_id: Optional agent filter.
            tool_id: Optional tool filter.
            limit: Maximum results.

        Returns:
            List of invocation dicts.
        """
        qs = MCPToolCall.objects.filter(tenant_id=tenant_id, called_at__isnull=False)
        if agent_id:
            qs = qs.filter(agent_id=agent_id)
        if tool_id:
            qs = qs.filter(tool_id=tool_id)

        invocations = qs.order_by("-called_at")[:limit]
        return [
            {
                "id": inv.id,
                "tool_id": inv.tool_id,
                "agent_id": inv.agent_id,
                "invocation_input": inv.invocation_input,
                "invocation_output": inv.invocation_output,
                "success": inv.success,
                "error_message": inv.error_message,
                "duration_ms": inv.duration_ms,
                "cost": float(inv.cost_per_call),
                "called_at": inv.called_at.isoformat() if inv.called_at else None,
            }
            for inv in invocations
        ]

    @staticmethod
    def _validate_schema(params: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        """Validate input params against a JSON Schema subset.

        Args:
            params: Input parameters.
            schema: JSON Schema dict.

        Returns:
            Dict with ``valid`` bool and optional ``errors`` list.
        """
        errors = []
        if schema.get("type") != "object":
            return {"valid": True}

        properties = schema.get("properties", {})
        required = schema.get("required", [])

        for key in required:
            if key not in params:
                errors.append(f"Missing required field: {key}")

        for key, value in params.items():
            prop_def = properties.get(key)
            if not prop_def:
                continue
            prop_type = prop_def.get("type")
            if prop_type == "string" and not isinstance(value, str):
                errors.append(f"Field {key} must be a string")
            elif prop_type == "integer" and not isinstance(value, int):
                errors.append(f"Field {key} must be an integer")
            elif prop_type == "number" and not isinstance(value, (int, float)):
                errors.append(f"Field {key} must be a number")
            elif prop_type == "array" and not isinstance(value, list):
                errors.append(f"Field {key} must be an array")
            elif prop_type == "object" and not isinstance(value, dict):
                errors.append(f"Field {key} must be an object")

            enum_values = prop_def.get("enum")
            if enum_values and value not in enum_values:
                errors.append(f"Field {key} must be one of {enum_values}")

        return {"valid": len(errors) == 0, "errors": errors}

    @staticmethod
    def _count_recent_calls(agent_id: int, tool_id: str, window_seconds: int) -> int:
        """Count recent invocations within the rate limit window.

        Args:
            agent_id: Agent primary key.
            tool_id: Tool identifier.
            window_seconds: Time window.

        Returns:
            Number of calls in the window.
        """
        since = timezone.now() - timezone.timedelta(seconds=window_seconds)
        return MCPToolCall.objects.filter(
            agent_id=agent_id,
            tool_id=tool_id,
            called_at__gte=since,
        ).count()
