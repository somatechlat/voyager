"""Team API views — combined router for all team collaboration endpoints.

Re-exports the unified router from task, channel, activity, and workload views.
"""

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

from .activity import router as activity_router
from .channels import router as channels_router
from .tasks import router as tasks_router

router = Router(auth=VoyagerKeycloakBearer())

router.add_router("/tasks", tasks_router, tags=["Tasks"])
router.add_router("/channels", channels_router, tags=["Channels"])
router.add_router("/activity", activity_router, tags=["Activity"])


@router.get("/health", tags=["Team"])
def module_health(request):
    """Team module health check."""
    return {"status": "ok", "module": "team"}
