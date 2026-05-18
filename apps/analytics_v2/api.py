"""Analytics v2 API router.

Wires all analytics sub-routers (dashboards, widgets, reports,
attribution, anomaly detection, exports, queries) into a single
router mounted at ``/api/v2/analytics/``.
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/health", tags=["Analytics"])
def module_health(request) -> dict[str, str]:
    """Analytics module health check."""
    return {"status": "ok", "module": "analytics_v2"}


# Import and register sub-routers
from apps.analytics_v2.views.anomaly import router as anomaly_router
from apps.analytics_v2.views.attribution import router as attribution_router
from apps.analytics_v2.views.dashboards import router as dashboards_router
from apps.analytics_v2.views.export import router as export_router
from apps.analytics_v2.views.queries import router as queries_router
from apps.analytics_v2.views.reports import router as reports_router

router.add_router("/dashboards", dashboards_router, tags=["Dashboards"])
router.add_router("/reports", reports_router, tags=["Reports"])
router.add_router("/attribution", attribution_router, tags=["Attribution"])
router.add_router("/anomaly", anomaly_router, tags=["Anomaly Detection"])
router.add_router("/exports", export_router, tags=["Exports"])
router.add_router("/queries", queries_router, tags=["Queries"])
