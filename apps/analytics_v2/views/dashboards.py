"""Dashboard CRUD and widget management views.

Provides Ninja endpoints for dashboard lifecycle (create, read, update,
delete), widget management, and dashboard data rendering.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.analytics_v2.models.dashboard import Dashboard, Widget
from apps.analytics_v2.serializers import (
    DashboardCreateIn,
    DashboardDataOut,
    DashboardOut,
    DashboardUpdateIn,
    WidgetCreateIn,
    WidgetDataIn,
    WidgetDataOut,
    WidgetOut,
    WidgetUpdateIn,
)
from apps.analytics_v2.services.dashboards import render_widget_data
from apps.analytics_v2.services.metrics import (
    get_comparison_modes,
    get_drill_paths,
    get_metric_catalog,
    get_widget_types,
)
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


def _tenant_from_request(request) -> str:
    """Extract tenant_id from the authenticated request."""
    return getattr(request, "tenant_id", "default")


def _user_from_request(request) -> str:
    """Extract user_id from the authenticated request."""
    user = getattr(request, "auth", None)
    if user and hasattr(user, "sub"):
        return str(user.sub)
    return "anonymous"


# ---------------------------------------------------------------------------
# Dashboard CRUD
# ---------------------------------------------------------------------------


@router.get("/dashboards", response=list[DashboardOut], tags=["Dashboards"])
def list_dashboards(request) -> list[Dashboard]:
    """List all dashboards for the current tenant."""
    tenant_id = _tenant_from_request(request)
    dashboards = Dashboard.objects.filter(tenant_id=tenant_id)
    return list(dashboards)


@router.get("/dashboards/{dashboard_id}", response=DashboardOut, tags=["Dashboards"])
def get_dashboard(request, dashboard_id: UUID) -> Dashboard:
    """Get a single dashboard with its widgets."""
    tenant_id = _tenant_from_request(request)
    dashboard = get_object_or_404(Dashboard, id=dashboard_id, tenant_id=tenant_id)
    return dashboard


@router.post("/dashboards", response=DashboardOut, tags=["Dashboards"])
def create_dashboard(request, payload: DashboardCreateIn) -> Dashboard:
    """Create a new dashboard."""
    tenant_id = _tenant_from_request(request)
    user_id = _user_from_request(request)

    dashboard = Dashboard.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        layout=payload.layout,
        filters=payload.filters,
        is_default=payload.is_default,
        is_shared=payload.is_shared,
        shared_with=payload.shared_with,
        created_by=user_id,
    )
    return dashboard


@router.patch("/dashboards/{dashboard_id}", response=DashboardOut, tags=["Dashboards"])
def update_dashboard(request, dashboard_id: UUID, payload: DashboardUpdateIn) -> Dashboard:
    """Update a dashboard's configuration."""
    tenant_id = _tenant_from_request(request)
    dashboard = get_object_or_404(Dashboard, id=dashboard_id, tenant_id=tenant_id)

    for attr in [
        "name",
        "description",
        "layout",
        "filters",
        "is_default",
        "is_shared",
        "shared_with",
    ]:
        val = getattr(payload, attr, None)
        if val is not None:
            setattr(dashboard, attr, val)
    dashboard.save()
    return dashboard


@router.delete("/dashboards/{dashboard_id}", tags=["Dashboards"])
def delete_dashboard(request, dashboard_id: UUID) -> dict[str, str]:
    """Delete a dashboard and all its widgets."""
    tenant_id = _tenant_from_request(request)
    dashboard = get_object_or_404(Dashboard, id=dashboard_id, tenant_id=tenant_id)
    dashboard.delete()
    return {"status": "deleted", "id": str(dashboard_id)}


# ---------------------------------------------------------------------------
# Widget management
# ---------------------------------------------------------------------------


@router.get("/dashboards/{dashboard_id}/widgets", response=list[WidgetOut], tags=["Widgets"])
def list_widgets(request, dashboard_id: UUID) -> list[Widget]:
    """List all widgets for a dashboard."""
    tenant_id = _tenant_from_request(request)
    get_object_or_404(Dashboard, id=dashboard_id, tenant_id=tenant_id)
    return list(Widget.objects.filter(dashboard_id=dashboard_id))


@router.post("/dashboards/{dashboard_id}/widgets", response=WidgetOut, tags=["Widgets"])
def create_widget(request, dashboard_id: UUID, payload: WidgetCreateIn) -> Widget:
    """Add a widget to a dashboard."""
    tenant_id = _tenant_from_request(request)
    dashboard = get_object_or_404(Dashboard, id=dashboard_id, tenant_id=tenant_id)

    widget = Widget.objects.create(
        dashboard=dashboard,
        widget_type=payload.widget_type,
        title=payload.title,
        subtitle=payload.subtitle,
        position=payload.position,
        config=payload.config,
        refresh_interval=payload.refresh_interval,
    )
    return widget


@router.get("/widgets/{widget_id}", response=WidgetOut, tags=["Widgets"])
def get_widget(request, widget_id: UUID) -> Widget:
    """Get a single widget."""
    tenant_id = _tenant_from_request(request)
    widget = get_object_or_404(Widget, id=widget_id, dashboard__tenant_id=tenant_id)
    return widget


@router.patch("/widgets/{widget_id}", response=WidgetOut, tags=["Widgets"])
def update_widget(request, widget_id: UUID, payload: WidgetUpdateIn) -> Widget:
    """Update a widget's configuration."""
    tenant_id = _tenant_from_request(request)
    widget = get_object_or_404(Widget, id=widget_id, dashboard__tenant_id=tenant_id)

    for attr in ["widget_type", "title", "subtitle", "position", "config", "refresh_interval"]:
        val = getattr(payload, attr, None)
        if val is not None:
            setattr(widget, attr, val)
    widget.save()
    return widget


@router.delete("/widgets/{widget_id}", tags=["Widgets"])
def delete_widget(request, widget_id: UUID) -> dict[str, str]:
    """Delete a widget."""
    tenant_id = _tenant_from_request(request)
    widget = get_object_or_404(Widget, id=widget_id, dashboard__tenant_id=tenant_id)
    widget.delete()
    return {"status": "deleted", "id": str(widget_id)}


# ---------------------------------------------------------------------------
# Dashboard & widget data rendering
# ---------------------------------------------------------------------------


@router.post("/widgets/{widget_id}/data", response=WidgetDataOut, tags=["Widgets"])
def get_widget_data(request, widget_id: UUID, payload: WidgetDataIn) -> dict[str, Any]:
    """Fetch and render data for a single widget."""
    tenant_id = _tenant_from_request(request)
    widget = get_object_or_404(Widget, id=widget_id, dashboard__tenant_id=tenant_id)

    date_range = payload.date_range or widget.config.get("date_range", {})
    filters = payload.filters or widget.dashboard.filters or {}

    data = render_widget_data(
        widget.widget_type,
        widget.config,
        date_range,
        filters,
        tenant_id,
    )

    return {
        "widget_id": widget.id,
        "widget_type": widget.widget_type,
        "title": widget.title,
        "data": data,
        "generated_at": __import__("datetime").datetime.utcnow(),
    }


@router.post("/dashboards/{dashboard_id}/data", response=DashboardDataOut, tags=["Dashboards"])
def get_dashboard_data(request, dashboard_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
    """Fetch and render data for all widgets on a dashboard."""
    tenant_id = _tenant_from_request(request)
    dashboard = get_object_or_404(Dashboard, id=dashboard_id, tenant_id=tenant_id)

    date_range = payload.get("date_range", {})
    filters = payload.get("filters", dashboard.filters or {})

    widgets_data = []
    for widget in dashboard.widgets.all():
        w_data = render_widget_data(
            widget.widget_type,
            widget.config,
            date_range,
            filters,
            tenant_id,
        )
        widgets_data.append(
            {
                "widget_id": widget.id,
                "widget_type": widget.widget_type,
                "title": widget.title,
                "data": w_data,
                "generated_at": __import__("datetime").datetime.utcnow(),
            }
        )

    return {
        "dashboard_id": dashboard.id,
        "name": dashboard.name,
        "widgets": widgets_data,
        "filters_applied": filters,
        "generated_at": __import__("datetime").datetime.utcnow(),
    }


# ---------------------------------------------------------------------------
# Catalog endpoints
# ---------------------------------------------------------------------------


@router.get("/catalog/widget-types", tags=["Catalog"])
def list_widget_types(request) -> dict[str, Any]:
    """Return the catalog of available widget types."""
    return {"widget_types": get_widget_types()}


@router.get("/catalog/metrics", tags=["Catalog"])
def list_metrics(request) -> dict[str, Any]:
    """Return the catalog of 100+ available metrics."""
    return {"metrics": get_metric_catalog()}


@router.get("/catalog/comparison-modes", tags=["Catalog"])
def list_comparison_modes(request) -> dict[str, Any]:
    """Return available comparison modes."""
    return {"comparison_modes": get_comparison_modes()}


@router.get("/catalog/drill-paths", tags=["Catalog"])
def list_drill_paths(request) -> dict[str, Any]:
    """Return available drill-down paths."""
    return {"drill_paths": get_drill_paths()}
