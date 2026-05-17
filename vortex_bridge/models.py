"""Pydantic models for Vortex API request/response validation.

These models mirror the Serde-derived structs in
``vortex-core/src/api.rs`` and provide runtime validation for
all payloads exchanged with the Vortex workflow engine.

All models use Pydantic v2 BaseModel with strict type checking.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────


class RunStatus(str, Enum):
    """Execution status values returned by Vortex.

    Mirrors ``crate::entities::run::RunStatus`` in the Rust source.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NotificationLevel(str, Enum):
    """Severity levels for real-time notifications."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


# ─────────────────────────────────────────────────────────────
# Graph lifecycle models
# ─────────────────────────────────────────────────────────────


class GraphRequest(BaseModel):
    """Request body for ``POST /api/graph`` — graph submission.

    Mirrors ``vortex_core::api::GraphRequest`` in the Rust source.
    """

    graph: Dict[str, Any] = Field(
        ...,
        description="GraphDSL definition as a JSON-serializable dict.",
    )
    priority: Optional[str] = Field(
        default=None,
        description="Execution priority: 'high' or 'low'.",
    )


class GraphResponse(BaseModel):
    """Response body for ``POST /api/graph``.

    Mirrors ``vortex_core::api::GraphResponse``.
    """

    graph_id: str = Field(..., description="UUID of the stored graph.")
    version: int = Field(..., description="Graph version number (starts at 1).")


class ExecuteRequest(BaseModel):
    """Request body for ``POST /api/graph/:id/execute``.

    Mirrors ``vortex_core::api::ExecuteRequest``.
    """

    full: Optional[bool] = Field(
        default=True,
        description="Execute all nodes (True) or partial subset.",
    )
    output_nodes: Optional[List[str]] = Field(
        default=None,
        description="Node IDs to capture as execution outputs.",
    )


class ExecuteResponse(BaseModel):
    """Response body for ``POST /api/graph/:id/execute``.

    Mirrors ``vortex_core::api::ExecuteResponse``.
    """

    run_id: str = Field(..., description="UUID of the created run.")
    estimated_time_ms: int = Field(
        ...,
        description="Scheduler-estimated execution time in milliseconds.",
    )


# ─────────────────────────────────────────────────────────────
# Run monitoring models
# ─────────────────────────────────────────────────────────────


class RunStatusResponse(BaseModel):
    """Response body for ``GET /api/run/:id/status``.

    Mirrors ``vortex_core::api::RunStatusResponse``.
    """

    run_id: str = Field(..., description="UUID of the run.")
    status: str = Field(
        ...,
        description="Current status: Running, Completed, Failed, Cancelled.",
    )
    progress: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fractional progress from 0.0 to 1.0.",
    )
    current_node: Optional[str] = Field(
        default=None,
        description="ID of the node currently executing, if any.",
    )


# ─────────────────────────────────────────────────────────────
# MCP (Model Context Protocol) models
# ─────────────────────────────────────────────────────────────


class RegisterMcpClientRequest(BaseModel):
    """Request body for ``POST /api/mcp/client/register``.

    Mirrors ``vortex_core::api::RegisterMcpClientRequest``.
    """

    id: str = Field(..., min_length=1, description="Unique client identifier.")
    command: str = Field(..., min_length=1, description="Executable command path.")
    args: List[str] = Field(
        default_factory=list,
        description="Command-line arguments for the MCP server.",
    )


class McpToolCallRequest(BaseModel):
    """Request body for ``POST /api/mcp/tool/call``.

    Mirrors ``vortex_core::api::McpToolCallRequest``.
    """

    type_id: str = Field(
        ...,
        description="VORTEX node type identifier, e.g. 'vortex.file.read'.",
    )
    arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tool-specific arguments.",
    )


class McpToolCallResponse(BaseModel):
    """Response body for ``POST /api/mcp/tool/call``.

    Mirrors ``vortex_core::api::McpToolCallResponse``.
    """

    type_id: str = Field(..., description="The type_id that was invoked.")
    result: Dict[str, Any] = Field(
        ...,
        description="Tool result as a JSON-serializable dictionary.",
    )


class NodeDef(BaseModel):
    """Node definition returned by ``GET /api/nodes/mcp``.

    Mirrors ``vortex_protocol::graph::NodeDef`` from the Vortex
    protocol crate.
    """

    type_id: str = Field(..., description="Fully-qualified node type ID.")
    name: str = Field(..., description="Human-readable node name.")
    description: Optional[str] = Field(
        default=None,
        description="Markdown description of node functionality.",
    )
    inputs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Input port definitions.",
    )
    outputs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Output port definitions.",
    )
    parameters: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Configurable parameter schema.",
    )


# ─────────────────────────────────────────────────────────────
# Health & error models
# ─────────────────────────────────────────────────────────────


class HealthCheckResponse(BaseModel):
    """Response body for ``GET /health``.

    Parsed from the JSON returned by Vortex's health_check handler.
    """

    status: str = Field(..., description="'healthy' or 'degraded'.")
    version: str = Field(..., description="Vortex build version.")
    checks: Dict[str, bool] = Field(
        default_factory=dict,
        description="Named dependency health flags.",
    )


class VortexError(BaseModel):
    """Error response body returned by Vortex on failure.

    Mirrors ``vortex_core::api::ErrorResponse``.
    """

    error: str = Field(..., description="Human-readable error message.")
    code: str = Field(..., description="Machine-readable error code.")


# ─────────────────────────────────────────────────────────────
# WebSocket message models (for reference / client use)
# ─────────────────────────────────────────────────────────────


class WsProgressMessage(BaseModel):
    """Progress update delivered over Vortex WebSocket.

    Mirrors ``WsMessage::Progress`` from ``vortex_core::api::WsMessage``.
    """

    type: str = Field(default="Progress")
    run_id: str
    node_id: str
    progress: float = Field(ge=0.0, le=1.0)


class WsNodeCompleteMessage(BaseModel):
    """Node completion message from Vortex WebSocket.

    Mirrors ``WsMessage::NodeComplete``.
    """

    type: str = Field(default="NodeComplete")
    run_id: str
    node_id: str
    duration_ms: int


class WsRunCompleteMessage(BaseModel):
    """Run completion message from Vortex WebSocket.

    Mirrors ``WsMessage::RunComplete``.
    """

    type: str = Field(default="RunComplete")
    run_id: str
    success: bool
    error: Optional[str] = None
