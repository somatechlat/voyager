"""Activity feed and workload API endpoints for team collaboration.

Provides activity feed querying, statistics, and workload/capacity endpoints.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.team.models import ActivityFeed
from apps.team.serializers import (
    ActivityCreateSchema,
    ActivityFilterSchema,
    ActivityListResponseSchema,
    ActivityStatsSchema,
    CapacityCheckSchema,
    CapacityResponseSchema,
    WorkloadResponseSchema,
)
from apps.team.services.activity import ActivityService
from apps.team.services.workload import WorkloadService

router = Router(auth=VoyagerKeycloakBearer())


def _activity_to_dict(entry: ActivityFeed) -> dict[str, Any]:
    """Serialize an ActivityFeed entry to a dict matching ActivitySchema."""
    return {
        "id": entry.id,
        "tenant_id": entry.tenant_id,
        "actor_id": entry.actor_id,
        "action_type": entry.action_type,
        "target_type": entry.target_type,
        "target_id": entry.target_id,
        "metadata": entry.metadata or {},
        "created_at": entry.created_at,
    }


# -- Activity feed -------------------------------------------------------


@router.get("", response=ActivityListResponseSchema)
def list_activity(request, filters: ActivityFilterSchema):
    """Query the activity feed with optional filters."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    result = ActivityService.get_feed(
        tenant_id=tenant_id,
        actor_id=filters.actor_id,
        action_type=filters.action_type,
        target_type=filters.target_type,
        target_id=filters.target_id,
        date_from=filters.date_from,
        date_to=filters.date_to,
        page=filters.page,
        page_size=filters.page_size,
    )
    return {
        "items": [_activity_to_dict(e) for e in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }


@router.post("")
def log_activity(request, payload: ActivityCreateSchema):
    """Manually log an activity feed entry."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    actor_id = payload.actor_id or getattr(user, "user_id", "")
    entry = ActivityService.log_activity(
        tenant_id=tenant_id,
        actor_id=actor_id,
        action_type=payload.action_type,
        target_type=payload.target_type,
        target_id=payload.target_id,
        metadata=payload.metadata,
    )
    return _activity_to_dict(entry)


@router.get("/stats", response=ActivityStatsSchema)
def activity_stats(
    request,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    """Get aggregated activity statistics."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    stats = ActivityService.get_stats(tenant_id=tenant_id, date_from=date_from, date_to=date_to)
    return ActivityStatsSchema(**stats)


# -- Workload ------------------------------------------------------------


@router.get("/workload", response=WorkloadResponseSchema)
def get_workload(
    request,
    user_ids: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
):
    """Get team workload overview.

    Args:
        user_ids: Comma-separated list of user IDs (empty = all).
        date_from: Start date filter.
        date_to: End date filter.
    """
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    uid_list = [u.strip() for u in user_ids.split(",") if u.strip()] or None
    result = WorkloadService.get_team_workload(
        tenant_id=tenant_id,
        user_ids=uid_list,
        date_from=date_from,
        date_to=date_to,
    )
    return result


# -- Capacity planning ---------------------------------------------------


@router.post("/capacity", response=CapacityResponseSchema)
def check_capacity(request, payload: CapacityCheckSchema):
    """Analyze team capacity and detect overload."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    result = WorkloadService.check_capacity(
        tenant_id=tenant_id,
        user_ids=payload.user_ids or None,
        date_from=payload.date_from,
        date_to=payload.date_to,
    )
    return result


@router.get("/overdue")
def get_overdue_tasks(
    request,
    assignee_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
):
    """Get overdue tasks."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    result = WorkloadService.get_overdue_tasks(
        tenant_id=tenant_id,
        assignee_id=assignee_id,
        page=page,
        page_size=page_size,
    )
    return result


@router.get("/upcoming-deadlines")
def get_upcoming_deadlines(
    request,
    days: int = 7,
    assignee_id: str | None = None,
    page_size: int = 50,
):
    """Get tasks with upcoming deadlines."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    result = WorkloadService.get_upcoming_deadlines(
        tenant_id=tenant_id,
        days=days,
        assignee_id=assignee_id,
        page_size=page_size,
    )
    return result
