"""Queue management views for publish queue operations."""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

from ..models import PublishQueue, ScheduledPost
from ..services.queue import QueueManager

router = Router(auth=VoyagerKeycloakBearer())


class QueuePriorityIn:
    """Input for updating queue priority."""

    priority: int  # 0=urgent, 3=low


class QueueBulkIn:
    """Input for bulk queue operations."""

    post_ids: list[str]
    action: str  # prioritize, deprioritize, remove


@router.get("/queue", response=dict, tags=["Publishing Queue"])
def queue_status(request) -> dict[str, Any]:
    """Get queue status for current tenant."""
    tenant_id = getattr(request, "tenant_id", "default")
    manager = QueueManager(tenant_id)
    return manager.get_queue_status()


@router.get("/queue/pending", response=list, tags=["Publishing Queue"])
def queue_pending(request) -> list[dict[str, Any]]:
    """Get pending queue entries."""
    tenant_id = getattr(request, "tenant_id", "default")
    entries = PublishQueue.objects.filter(
        scheduled_post__tenant_id=tenant_id,
        processed_at__isnull=True,
    ).select_related("scheduled_post").order_by("queue_priority", "next_retry_at")[:50]

    return [_entry_to_dict(e) for e in entries]


@router.post("/queue/posts/{post_id}/enqueue", response=dict, tags=["Publishing Queue"])
def enqueue_post(request, post_id: str) -> dict[str, Any]:
    """Add a post to the queue."""
    tenant_id = getattr(request, "tenant_id", "default")
    post = get_object_or_404(ScheduledPost, id=post_id, tenant_id=tenant_id)
    manager = QueueManager(tenant_id)
    entry = manager.enqueue(post)
    return {"success": True, "queue_id": str(entry.id)}


@router.delete("/queue/posts/{post_id}/dequeue", response=dict, tags=["Publishing Queue"])
def dequeue_post(request, post_id: str) -> dict[str, Any]:
    """Remove a post from the queue."""
    tenant_id = getattr(request, "tenant_id", "default")
    manager = QueueManager(tenant_id)
    manager.dequeue(post_id)
    return {"success": True}


@router.post("/queue/posts/{post_id}/priority", response=dict, tags=["Publishing Queue"])
def set_priority(request, post_id: str, payload: QueuePriorityIn) -> dict[str, Any]:
    """Set queue priority for a post."""
    tenant_id = getattr(request, "tenant_id", "default")
    post = get_object_or_404(ScheduledPost, id=post_id, tenant_id=tenant_id)
    manager = QueueManager(tenant_id)
    entry = manager.enqueue(post, payload.priority)
    return {"success": True, "queue_id": str(entry.id), "priority": entry.queue_priority}


@router.post("/queue/bulk", response=dict, tags=["Publishing Queue"])
def bulk_queue_action(request, payload: QueueBulkIn) -> dict[str, Any]:
    """Bulk queue operations."""
    tenant_id = getattr(request, "tenant_id", "default")
    manager = QueueManager(tenant_id)

    processed = 0
    for post_id in payload.post_ids:
        try:
            post = ScheduledPost.objects.get(id=post_id, tenant_id=tenant_id)
            if payload.action == "prioritize":
                manager.enqueue(post, 0)
            elif payload.action == "deprioritize":
                manager.enqueue(post, 3)
            elif payload.action == "remove":
                manager.dequeue(post_id)
            processed += 1
        except ScheduledPost.DoesNotExist:
            continue

    return {"success": True, "processed": processed, "action": payload.action}


@router.get("/queue/overflow/{post_id}", response=dict, tags=["Publishing Queue"])
def check_overflow(request, post_id: str) -> dict[str, Any]:
    """Check if a post would overflow frequency limits."""
    tenant_id = getattr(request, "tenant_id", "default")
    post = get_object_or_404(ScheduledPost, id=post_id, tenant_id=tenant_id)
    manager = QueueManager(tenant_id)
    return manager.check_overflow(post)


def _entry_to_dict(entry: PublishQueue) -> dict[str, Any]:
    """Convert queue entry to dict."""
    post = entry.scheduled_post
    return {
        "id": str(entry.id),
        "post_id": str(post.id),
        "platform": post.platform,
        "caption": post.caption[:100] if post.caption else "",
        "scheduled_at": post.scheduled_at.isoformat(),
        "status": post.status,
        "priority": entry.queue_priority,
        "retry_count": entry.retry_count,
        "next_retry_at": entry.next_retry_at.isoformat() if entry.next_retry_at else None,
        "overflow_reason": entry.overflow_reason or "",
        "created_at": entry.created_at.isoformat(),
    }
