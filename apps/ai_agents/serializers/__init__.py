"""Pydantic schemas (Django Ninja Serializers) for AI Agents.

Re-exports all schemas from submodules for convenience.
"""

from .agents import (
    AgentConfigSchema,
    AgentCreateSchema,
    AgentListResponse,
    AgentResourcesSchema,
    AgentSchema,
    AgentUpdateSchema,
    RunAgentRequest,
    RunAgentResponse,
)
from .collaboration import (
    ActiveCollaborationsResponse,
    CollaborationSchema,
    CompleteCollaborationRequest,
    CreateCollaborationRequest,
    DelegateTaskRequest,
    DelegateTaskResponse,
)
from .context import (
    AssembleContextRequest,
    AssembledContextResponse,
    ContextListResponse,
    ContextSnapshotSchema,
)
from .learning import (
    ABTestConfigRequest,
    ABTestResultRequest,
    ABTestStatusResponse,
    LearningLoopSchema,
    OutcomeAnalysisRequest,
    OutcomeAnalysisResponse,
    UpdateStrategyRequest,
)
from .mcp import (
    InvokeToolRequest,
    InvokeToolResponse,
    MCPToolSchema,
    RegisterToolRequest,
    ToolInvocationListResponse,
    ToolInvocationSchema,
)
from .memory import (
    ConsolidateMemoryResponse,
    MemoryEntrySchema,
    MemorySchema,
    SearchMemoryRequest,
    SearchMemoryResponse,
    SearchMemoryResult,
    StoreMemoryRequest,
    StoreMemoryResponse,
)
from .resources import (
    ConsumeResourcesRequest,
    ResourceCheckResponse,
    ResourceLimitSchema,
    ResourceStatusSchema,
    ResetResourcesResponse,
)

__all__ = [
    "ABTestConfigRequest",
    "ABTestResultRequest",
    "ABTestStatusResponse",
    "ActiveCollaborationsResponse",
    "AgentConfigSchema",
    "AgentCreateSchema",
    "AgentListResponse",
    "AgentResourcesSchema",
    "AgentSchema",
    "AgentUpdateSchema",
    "AssembleContextRequest",
    "AssembledContextResponse",
    "CollaborationSchema",
    "CompleteCollaborationRequest",
    "ConsolidateMemoryResponse",
    "ConsumeResourcesRequest",
    "ContextListResponse",
    "ContextSnapshotSchema",
    "CreateCollaborationRequest",
    "DelegateTaskRequest",
    "DelegateTaskResponse",
    "InvokeToolRequest",
    "InvokeToolResponse",
    "LearningLoopSchema",
    "MCPToolSchema",
    "MemoryEntrySchema",
    "MemorySchema",
    "OutcomeAnalysisRequest",
    "OutcomeAnalysisResponse",
    "RegisterToolRequest",
    "ResetResourcesResponse",
    "ResourceCheckResponse",
    "ResourceLimitSchema",
    "ResourceStatusSchema",
    "RunAgentRequest",
    "RunAgentResponse",
    "SearchMemoryRequest",
    "SearchMemoryResponse",
    "SearchMemoryResult",
    "StoreMemoryRequest",
    "StoreMemoryResponse",
    "ToolInvocationListResponse",
    "ToolInvocationSchema",
    "UpdateStrategyRequest",
]
