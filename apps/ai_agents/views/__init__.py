"""AI Agents API views.

Registers all AI agent endpoints from submodules: agent CRUD,
memory management, context assembly, collaboration, MCP tools,
learning loops, and resource monitoring.
"""

from ninja import Router

from apps.ai_agents.serializers.agents import (
    AgentListResponse,
    AgentSchema,
    RunAgentResponse,
)
from apps.ai_agents.serializers.collaboration import (
    ActiveCollaborationsResponse,
    CollaborationSchema,
    DelegateTaskResponse,
)
from apps.ai_agents.serializers.context import (
    AssembledContextResponse,
    ContextListResponse,
)
from apps.ai_agents.serializers.learning import (
    ABTestStatusResponse,
    LearningLoopSchema,
    OutcomeAnalysisResponse,
)
from apps.ai_agents.serializers.mcp import (
    InvokeToolResponse,
    MCPToolSchema,
    ToolInvocationListResponse,
)
from apps.ai_agents.serializers.memory import (
    ConsolidateMemoryResponse,
    MemoryEntrySchema,
    MemorySchema,
    SearchMemoryResponse,
    StoreMemoryResponse,
)
from apps.ai_agents.serializers.resources import (
    ResourceCheckResponse,
    ResourceLimitSchema,
    ResourceStatusSchema,
    ResetResourcesResponse,
)
from apps.rbac.auth import VoyagerKeycloakBearer

from .agents import (
    create_agent,
    delete_agent,
    get_agent,
    list_agents,
    run_agent,
    update_agent,
)
from .collaboration import (
    complete_collaboration,
    create_collaboration,
    delegate_task,
    get_collaboration_messages,
    list_active_collaborations,
)
from .context import assemble_context, list_contexts
from .learning import (
    analyze_outcomes,
    configure_ab_test,
    list_learning_loops,
    record_ab_result,
    update_strategy,
)
from .mcp import get_invocations, invoke_tool, list_tools, register_tool
from .memory import (
    consolidate_memory,
    delete_memory,
    get_memory_entries,
    get_memory_info,
    search_memory,
    store_memory,
)
from .resources import (
    check_resources,
    consume_resources,
    get_resource_limits,
    get_resource_status,
    reset_daily_counters,
)

router = Router(auth=VoyagerKeycloakBearer())

# Agent CRUD endpoints
router.post("/agents", response=AgentSchema, tags=["Agents"])(create_agent)
router.get("/agents", response=AgentListResponse, tags=["Agents"])(list_agents)
router.get("/agents/{agent_id}", response=AgentSchema, tags=["Agents"])(get_agent)
router.put("/agents/{agent_id}", response=AgentSchema, tags=["Agents"])(update_agent)
router.delete("/agents/{agent_id}", tags=["Agents"])(delete_agent)
router.post("/agents/{agent_id}/run", response=RunAgentResponse, tags=["Agents"])(run_agent)

# Memory management endpoints
router.get("/agents/{agent_id}/memory", response=MemorySchema, tags=["Memory"])(get_memory_info)
router.get(
    "/agents/{agent_id}/memory/entries",
    response=list[MemoryEntrySchema],
    tags=["Memory"],
)(get_memory_entries)
router.post("/agents/{agent_id}/memory", response=StoreMemoryResponse, tags=["Memory"])(store_memory)
router.post(
    "/agents/{agent_id}/memory/search",
    response=SearchMemoryResponse,
    tags=["Memory"],
)(search_memory)
router.delete("/agents/{agent_id}/memory/{qdrant_id}", tags=["Memory"])(delete_memory)
router.post(
    "/agents/{agent_id}/memory/consolidate",
    response=ConsolidateMemoryResponse,
    tags=["Memory"],
)(consolidate_memory)

# Context assembly endpoints
router.post(
    "/agents/{agent_id}/context",
    response=AssembledContextResponse,
    tags=["Context"],
)(assemble_context)
router.get(
    "/agents/{agent_id}/context",
    response=ContextListResponse,
    tags=["Context"],
)(list_contexts)

# Collaboration endpoints
router.post(
    "/collaborations",
    response=CollaborationSchema,
    tags=["Collaboration"],
)(create_collaboration)
router.get(
    "/collaborations/active",
    response=ActiveCollaborationsResponse,
    tags=["Collaboration"],
)(list_active_collaborations)
router.post(
    "/collaborations/{collaboration_id}/delegate",
    response=DelegateTaskResponse,
    tags=["Collaboration"],
)(delegate_task)
router.post(
    "/collaborations/{collaboration_id}/complete",
    response=dict,
    tags=["Collaboration"],
)(complete_collaboration)
router.get(
    "/collaborations/{collaboration_id}/messages",
    response=list[dict],
    tags=["Collaboration"],
)(get_collaboration_messages)

# MCP tool endpoints
router.post("/tools/register", response=MCPToolSchema, tags=["MCP Tools"])(register_tool)
router.get("/tools", response=list[MCPToolSchema], tags=["MCP Tools"])(list_tools)
router.post(
    "/tools/{tool_id}/invoke/{agent_id}",
    response=InvokeToolResponse,
    tags=["MCP Tools"],
)(invoke_tool)
router.get(
    "/tools/invocations",
    response=ToolInvocationListResponse,
    tags=["MCP Tools"],
)(get_invocations)

# Learning loop endpoints
router.post(
    "/agents/{agent_id}/learn/analyze",
    response=OutcomeAnalysisResponse,
    tags=["Learning"],
)(analyze_outcomes)
router.post(
    "/agents/{agent_id}/learn/update",
    response=LearningLoopSchema,
    tags=["Learning"],
)(update_strategy)
router.get(
    "/agents/{agent_id}/learn",
    response=list[LearningLoopSchema],
    tags=["Learning"],
)(list_learning_loops)
router.post(
    "/agents/{agent_id}/learn/abtest",
    response=dict,
    tags=["Learning"],
)(configure_ab_test)
router.post(
    "/agents/{agent_id}/learn/abresult",
    response=ABTestStatusResponse,
    tags=["Learning"],
)(record_ab_result)

# Resource monitoring endpoints
router.get(
    "/agents/{agent_id}/resources",
    response=ResourceStatusSchema,
    tags=["Resources"],
)(get_resource_status)
router.get(
    "/agents/{agent_id}/resources/limits",
    response=ResourceLimitSchema,
    tags=["Resources"],
)(get_resource_limits)
router.post(
    "/agents/{agent_id}/resources/check",
    response=ResourceCheckResponse,
    tags=["Resources"],
)(check_resources)
router.post(
    "/agents/{agent_id}/resources/consume",
    response=ResourceStatusSchema,
    tags=["Resources"],
)(consume_resources)
router.post(
    "/resources/reset",
    response=ResetResourcesResponse,
    tags=["Resources"],
)(reset_daily_counters)
