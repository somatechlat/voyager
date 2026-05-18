"""AI Agents API.

Endpoints for managing AI marketing agents — agent creation,
prompt management, execution, memory (Qdrant), and MCP tool calls.

All endpoints are registered in ``apps.ai_agents.views`` and re-exported here.
"""

from apps.ai_agents.views import router  # noqa: F401
