"""MCP (Model Context Protocol) tool call model."""

from __future__ import annotations

from django.db import models


class MCPToolCall(models.Model):
    """Record of an MCP tool registration or invocation.

    Tracks tool definitions (with input/output schemas), invocation logs,
    rate limiting state, and per-call cost accounting.

    Attributes:
        id: Auto-incrementing primary key.
        agent: The agent that registered or invoked this tool.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        tool_id: Unique tool identifier (e.g., tool_seo_analyzer).
        name: Human-readable tool name.
        description: Tool description.
        version: Semantic version string.
        input_schema: JSON Schema for tool inputs.
        output_schema: JSON Schema for tool outputs.
        endpoint: URL or internal path to invoke the tool.
        rate_limit_max_calls: Max calls per window.
        rate_limit_window_seconds: Rate limit window in seconds.
        timeout_ms: Execution timeout in milliseconds.
        cost_per_call: Cost in dollars per invocation.
        invocation_input: Input params for an invocation.
        invocation_output: Output result for an invocation.
        success: Whether the invocation succeeded.
        error_message: Error text if the invocation failed.
        duration_ms: Actual execution duration in milliseconds.
        called_at: When the tool was invoked.
        created_at: Creation timestamp.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    agent = models.ForeignKey(
        "ai_agents.AIAgent",
        on_delete=models.CASCADE,
        related_name="tool_calls",
        help_text="The agent that registered or invoked this tool",
    )
    tenant_id = models.CharField(
        max_length=128, db_index=True, help_text="Tenant identifier for multi-tenancy isolation"
    )
    tool_id = models.CharField(
        max_length=128, db_index=True, help_text="Unique tool identifier"
    )
    name = models.CharField(max_length=255, help_text="Human-readable tool name")
    description = models.TextField(blank=True, help_text="Tool description")
    version = models.CharField(max_length=20, default="1.0.0", help_text="Semantic version string")
    input_schema = models.JSONField(
        default=dict, blank=True, help_text="JSON Schema for tool inputs"
    )
    output_schema = models.JSONField(
        default=dict, blank=True, help_text="JSON Schema for tool outputs"
    )
    endpoint = models.CharField(
        max_length=500, blank=True, help_text="URL or internal path to invoke the tool"
    )
    rate_limit_max_calls = models.IntegerField(
        default=100, help_text="Max calls per rate limit window"
    )
    rate_limit_window_seconds = models.IntegerField(
        default=3600, help_text="Rate limit window in seconds"
    )
    timeout_ms = models.IntegerField(
        default=30000, help_text="Execution timeout in milliseconds"
    )
    cost_per_call = models.DecimalField(
        max_digits=8, decimal_places=6, default=0.010000, help_text="Cost in dollars per invocation"
    )
    invocation_input = models.JSONField(
        default=dict, blank=True, help_text="Input params for an invocation"
    )
    invocation_output = models.JSONField(
        default=dict, blank=True, help_text="Output result for an invocation"
    )
    success = models.BooleanField(
        null=True, blank=True, help_text="Whether the invocation succeeded"
    )
    error_message = models.TextField(
        blank=True, help_text="Error text if the invocation failed"
    )
    duration_ms = models.IntegerField(
        null=True, blank=True, help_text="Actual execution duration in milliseconds"
    )
    called_at = models.DateTimeField(
        null=True, blank=True, help_text="When the tool was invoked"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="Timestamp when the record was created"
    )

    class Meta:
        db_table = "voyager_mcp_tool_call"
        verbose_name = "MCP Tool Call"
        verbose_name_plural = "MCP Tool Calls"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "tool_id"]),
            models.Index(fields=["agent", "tool_id", "-created_at"]),
            models.Index(fields=["agent", "success"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.tool_id})"
