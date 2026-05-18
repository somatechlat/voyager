"""
Workflows v2 API.

Endpoints for workflow automation — workflow design (Vortex integration),
execution tracking, template management, approval chains, scheduling.

Router sub-mounts:
    /workflows              → Workflow CRUD + versioning + validation/simulation
    /workflows/{id}/nodes   → Node management
    /workflows/{id}/edges   → Edge management
    /workflows/{id}/triggers → Trigger configuration
    /workflows/{id}/executions → Execution monitoring
    /workflows/{id}/executions/{id}/approvals → Human approval actions
    /templates/marketplace  → Template marketplace
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.workflows_v2.views.execution import router as execution_router
from apps.workflows_v2.views.human_loop import router as approvals_router
from apps.workflows_v2.views.nodes import router as nodes_router
from apps.workflows_v2.views.templates import router as templates_router
from apps.workflows_v2.views.triggers import router as triggers_router
from apps.workflows_v2.views.workflows import router as workflows_router

router = Router(auth=VoyagerKeycloakBearer())

# Mount all sub-routers
router.add_router("", workflows_router, tags=["Workflows"])
router.add_router("", nodes_router, tags=["Workflow Nodes"])
router.add_router("", triggers_router, tags=["Triggers"])
router.add_router("", execution_router, tags=["Executions"])
router.add_router("", approvals_router, tags=["Human Approval"])
router.add_router("", templates_router, tags=["Templates"])


@router.get("/health", tags=["Workflows"])
def module_health(request) -> dict[str, str]:
    """Workflows module health check."""
    return {"status": "ok", "module": "workflows_v2"}
