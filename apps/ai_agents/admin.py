"""Django Admin for AI Agents app.

Registers AIAgent, AgentMemory, MemoryEntry, AgentContext,
and AgentCollaboration models.
"""

from __future__ import annotations

import json

from django.contrib import admin

from apps.ai_agents.models import (
    AgentCollaboration,
    AgentContext,
    AgentLearning,
    AgentMemory,
    AIAgent,
    MCPConnection,
    MCPRegistry,
    MemoryEntry,
)


class _JSONMixin:
    """Mixin for formatting JSON fields."""

    @staticmethod
    def _format_json(value: object, max_len: int = 200) -> str:
        if not value:
            return "—"
        if isinstance(value, (dict, list)):
            text = json.dumps(value, indent=2, default=str)
            if len(text) > max_len:
                return text[:max_len] + "..."
            return text
        return str(value)[:max_len]


class _TenantIdMixin:
    """Mixin for shortening tenant_id display."""

    @admin.display(description="Tenant")
    def tenant_id_short(self, obj):
        tid = getattr(obj, "tenant_id", "")
        return tid[:12] + "..." if len(str(tid)) > 12 else str(tid)


class MemoryEntryInline(admin.TabularInline):
    """Inline for MemoryEntry within AgentMemory."""

    model = MemoryEntry
    extra = 0
    readonly_fields = ("id", "created_at")


@admin.register(AIAgent)
class AIAgentAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for AIAgent model."""

    list_display = (
        "name",
        "agent_type",
        "model_provider",
        "status",
        "is_active",
        "version",
        "total_runs",
        "success_rate_display",
        "tenant_id_short",
        "created_at",
    )
    list_filter = (
        "agent_type",
        "model_provider",
        "status",
        "is_active",
        "created_at",
    )
    search_fields = ("name", "description", "tenant_id")
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "total_runs",
        "success_count",
        "failure_count",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Success Rate")
    def success_rate_display(self, obj: AIAgent) -> str:
        return f"{obj.success_rate:.1f}%"

    @admin.display(description="Config")
    def display_config(self, obj: AIAgent) -> str:
        return self._format_json(obj.config_json, 200)

    @admin.display(description="Tools")
    def display_tools(self, obj: AIAgent) -> str:
        return self._format_json(obj.tools_json, 150)

    @admin.display(description="System Prompt")
    def display_prompt(self, obj: AIAgent) -> str:
        prompt = obj.system_prompt
        if len(prompt) > 100:
            return prompt[:100] + "..."
        return prompt


@admin.register(AgentMemory)
class AgentMemoryAdmin(_JSONMixin, admin.ModelAdmin):
    """Admin for AgentMemory model."""

    list_display = (
        "agent_name",
        "memory_type",
        "retrieval_count",
        "importance_score",
        "is_active",
        "created_at",
    )
    list_filter = ("memory_type", "is_active", "created_at")
    search_fields = ("agent__name",)
    ordering = ("-importance_score",)
    readonly_fields = ("id", "retrieval_count", "created_at", "updated_at")
    list_select_related = ("agent",)
    inlines = [MemoryEntryInline]

    @admin.display(description="Agent")
    def agent_name(self, obj: AgentMemory) -> str:
        return obj.agent.name if obj.agent else "—"

    @admin.display(description="Embedding Preview")
    def display_embedding(self, obj: AgentMemory) -> str:
        emb = obj.embedding_json
        if isinstance(emb, list) and len(emb) > 0:
            return f"[{len(emb)} dims] first: {emb[0]:.4f}"
        return "—"


@admin.register(MemoryEntry)
class MemoryEntryAdmin(_JSONMixin, admin.ModelAdmin):
    """Admin for MemoryEntry model."""

    list_display = (
        "memory_agent",
        "role",
        "tokens",
        "model",
        "latency_ms",
        "created_at",
    )
    list_filter = ("role", "model", "created_at")
    search_fields = ("content", "tool_calls_json")
    ordering = ("-created_at",)
    readonly_fields = ("id", "tokens", "latency_ms", "created_at")
    list_select_related = ("memory",)

    @admin.display(description="Agent")
    def memory_agent(self, obj: MemoryEntry) -> str:
        return obj.memory.agent.name if obj.memory and obj.memory.agent else "—"

    @admin.display(description="Tool Calls")
    def display_tools(self, obj: MemoryEntry) -> str:
        return self._format_json(obj.tool_calls_json, 150)


@admin.register(AgentContext)
class AgentContextAdmin(_JSONMixin, admin.ModelAdmin):
    """Admin for AgentContext model."""

    list_display = (
        "agent_name",
        "session_id_short",
        "context_type",
        "is_active",
        "created_at",
        "updated_at",
    )
    list_filter = ("context_type", "is_active", "created_at")
    search_fields = ("session_id", "user_id")
    ordering = ("-updated_at",)
    readonly_fields = ("id", "created_at", "updated_at")
    list_select_related = ("agent",)

    @admin.display(description="Agent")
    def agent_name(self, obj: AgentContext) -> str:
        return obj.agent.name if obj.agent else "—"

    @admin.display(description="Session")
    def session_id_short(self, obj: AgentContext) -> str:
        sid = obj.session_id
        return sid[:12] + "..." if len(sid) > 12 else sid

    @admin.display(description="Variables")
    def display_variables(self, obj: AgentContext) -> str:
        return self._format_json(obj.variables_json, 200)


@admin.register(AgentCollaboration)
class AgentCollaborationAdmin(admin.ModelAdmin):
    """Admin for AgentCollaboration model."""

    list_display = (
        "initiator_name",
        "collaboration_type",
        "status",
        "priority",
        "started_at",
        "completed_at",
    )
    list_filter = ("collaboration_type", "status", "priority", "started_at")
    search_fields = ("goal",)
    ordering = ("-started_at",)
    readonly_fields = ("id", "started_at", "completed_at", "created_at", "updated_at")
    list_select_related = ("initiator_agent",)

    @admin.display(description="Initiator")
    def initiator_name(self, obj: AgentCollaboration) -> str:
        return obj.initiator_agent.name if obj.initiator_agent else "—"

    @admin.display(description="Agents")
    def display_agents(self, obj: AgentCollaboration) -> str:
        agents = obj.participating_agents.all()
        return ", ".join(a.name for a in agents[:5]) if agents else "—"


@admin.register(AgentLearning)
class AgentLearningAdmin(_JSONMixin, admin.ModelAdmin):
    """Admin for AgentLearning model."""

    list_display = (
        "agent_name",
        "feedback_type",
        "rating",
        "source",
        "created_at",
    )
    list_filter = ("feedback_type", "rating", "source", "created_at")
    search_fields = ("feedback_text", "task_description")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")
    list_select_related = ("agent",)

    @admin.display(description="Agent")
    def agent_name(self, obj: AgentLearning) -> str:
        return obj.agent.name if obj.agent else "—"

    @admin.display(description="Patterns")
    def display_patterns(self, obj: AgentLearning) -> str:
        return self._format_json(obj.learned_patterns, 200)


@admin.register(MCPRegistry)
class MCPRegistryAdmin(admin.ModelAdmin):
    """Admin for MCPRegistry model."""

    list_display = (
        "name",
        "mcp_type",
        "version",
        "is_active",
        "created_at",
    )
    list_filter = ("mcp_type", "is_active", "created_at")
    search_fields = ("name", "description", "endpoint_url")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(MCPConnection)
class MCPConnectionAdmin(admin.ModelAdmin):
    """Admin for MCPConnection model."""

    list_display = (
        "agent_name",
        "registry_name",
        "connection_type",
        "status",
        "last_used_at",
        "created_at",
    )
    list_filter = ("connection_type", "status", "created_at")
    search_fields = ("agent__name", "registry__name")
    ordering = ("-last_used_at",)
    readonly_fields = ("id", "last_used_at", "created_at", "updated_at")
    list_select_related = ("agent", "registry")

    @admin.display(description="Agent")
    def agent_name(self, obj: MCPConnection) -> str:
        return obj.agent.name if obj.agent else "—"

    @admin.display(description="Registry")
    def registry_name(self, obj: MCPConnection) -> str:
        return obj.registry.name if obj.registry else "—"
