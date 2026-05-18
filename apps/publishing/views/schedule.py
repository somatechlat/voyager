"""Schedule and publish endpoints for triggering content distribution."""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

from ..models import ScheduledPost
from ..services.publisher import publish_to_platforms
from ..services.scheduler import find_optimal_slot

router = Router(auth=VoyagerKeycloakBearer())


class PublishNowIn:
    """Input for immediate publish."""

    force: bool = False


class ScheduleBatchIn:
    """Input for batch scheduling."""

    post_ids: list[str]
    scheduled_at: str
    timezone: str = "UTC"


class OptimalSlotIn:
    """Input for optimal slot calculation."""

    platform: str
    account_id: str
    preferred_date: str


@router.post("/posts/{post_id}/publish", response=dict, tags=["Publishing Schedule"])
def publish_now(request, post_id: str, payload: PublishNowIn) -> dict[str, Any]:
    """Immediately publish a scheduled post."""
    tenant_id = getattr(request, "tenant_id", "default")
    post = get_object_or_404(ScheduledPost, id=post_id, tenant_id=tenant_id)

    if not post.can_publish() and not payload.force:
        return {
            "success": False,
            "error": "Post cannot be published. Not approved or not in valid state.",
            "status": post.status,
            "approval_status": post.approval_status,
        }

    result = publish_to_platforms(post)
    return {
        "success": result.get("success", False),
        "post_id": str(post.id),
        "platform": post.platform,
        "platform_post_id": result.get("platform_post_id"),
        "error": result.get("error"),
        "error_type": result.get("error_type"),
        "retryable": result.get("retryable", False),
    }


@router.post("/posts/{post_id}/schedule", response=dict, tags=["Publishing Schedule"])
def schedule_post(request, post_id: str, payload: ScheduleBatchIn) -> dict[str, Any]:
    """Schedule a post to a specific time."""
    tenant_id = getattr(request, "tenant_id", "default")
    post = get_object_or_404(ScheduledPost, id=post_id, tenant_id=tenant_id)

    from django.utils.dateparse import parse_datetime

    dt = parse_datetime(payload.scheduled_at)
    if not dt:
        return {"success": False, "error": "Invalid scheduled_at datetime"}

    post.scheduled_at = dt
    post.timezone = payload.timezone
    post.status = ScheduledPost.Status.SCHEDULED
    post.save(update_fields=["scheduled_at", "timezone", "status"])

    return {
        "success": True,
        "post_id": str(post.id),
        "scheduled_at": post.scheduled_at.isoformat(),
        "timezone": post.timezone,
        "status": post.status,
    }


@router.post("/schedule/batch", response=dict, tags=["Publishing Schedule"])
def batch_schedule(request, payload: ScheduleBatchIn) -> dict[str, Any]:
    """Batch schedule multiple posts."""
    tenant_id = getattr(request, "tenant_id", "default")

    from django.utils.dateparse import parse_datetime

    dt = parse_datetime(payload.scheduled_at)
    if not dt:
        return {"success": False, "error": "Invalid scheduled_at datetime"}

    updated = 0
    errors: list[str] = []

    for post_id in payload.post_ids:
        try:
            post = ScheduledPost.objects.get(id=post_id, tenant_id=tenant_id)
            post.scheduled_at = dt
            post.timezone = payload.timezone
            post.status = ScheduledPost.Status.SCHEDULED
            post.save(update_fields=["scheduled_at", "timezone", "status"])
            updated += 1
        except ScheduledPost.DoesNotExist:
            errors.append(f"Post {post_id} not found")

    return {
        "success": True,
        "updated": updated,
        "total": len(payload.post_ids),
        "errors": errors,
    }


@router.post("/schedule/optimal-slot", response=dict, tags=["Publishing Schedule"])
def optimal_slot(request, payload: OptimalSlotIn) -> dict[str, Any]:
    """Find optimal publishing slot."""
    tenant_id = getattr(request, "tenant_id", "default")

    from django.utils.dateparse import parse_datetime

    preferred = parse_datetime(payload.preferred_date)
    if not preferred:
        return {"success": False, "error": "Invalid preferred_date"}

    result = find_optimal_slot(
        tenant_id=tenant_id,
        platform=payload.platform,
        account_id=payload.account_id,
        preferred_date=preferred,
    )
    return {"success": True, "result": result}


@router.get("/posts/{post_id}/status", response=dict, tags=["Publishing Schedule"])
def get_publish_status(request, post_id: str) -> dict[str, Any]:
    """Get publishing status of a post."""
    tenant_id = getattr(request, "tenant_id", "default")
    post = get_object_or_404(ScheduledPost, id=post_id, tenant_id=tenant_id)
    return {
        "post_id": str(post.id),
        "status": post.status,
        "platform": post.platform,
        "platform_post_id": post.platform_post_id or None,
        "publish_attempts": post.publish_attempts,
        "last_attempt_at": post.last_attempt_at.isoformat() if post.last_attempt_at else None,
        "last_error": post.last_error or None,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "can_publish": post.can_publish(),
        "is_due": post.is_due(),
    }
