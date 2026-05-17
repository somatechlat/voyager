"""
AI Agents API.

Endpoints for managing AI marketing agents — agent creation,
prompt management, execution, memory (Qdrant), and MCP tool calls.
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/health", tags=["AI Agents"])
def module_health(request):
    """AI Agents module health check."""
    return {"status": "ok", "module": "ai_agents"}
