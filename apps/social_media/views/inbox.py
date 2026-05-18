"""Unified inbox views.

Endpoints for message listing, threading, assignment, and reply.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.social_media.models import InboxMessage
from apps.social_media.services.inbox import aggregate_messages, thread_messages

router = Router(auth=VoyagerKeycloakBearer())


class MessageIn:
    """Input schema for creating an inbox message."""

    platform: str
    type: str
    text: str = ""
    author_name: str = ""
    author_platform_id: str = ""
    author_avatar: str = ""
    media_urls: list[str] = []
    parent_id: str | None = None
    post_id: str = ""
    thread_id: str | None = None
    received_at: str = ""


class MessageOut:
    """Output schema for an inbox message."""

    id: str
    platform: str
    type: str
    author_name: str
    author_avatar: str
    text: str
    status: str
    sentiment: str
    sentiment_score: float
    spam_score: float
    assigned_to: str
    replied_at: str | None
    response_time_minutes: int | None
    received_at: str
    created_at: str


class ReplyIn:
    """Input schema for replying to a message."""

    reply_text: str


class AssignIn:
    """Input schema for assigning a message."""

    assigned_to: str
    assignment_reason: str = ""


class BulkStatusIn:
    """Input schema for bulk status update."""

    ids: list[str]
    status: str


@router.get("/messages", response=list[MessageOut], tags=["SM Inbox"])
def list_messages(
    request,
    tenant_id: str = "",
    platform: str = "",
    status: str = "",
    type: str = "",
    assigned_to: str = "",
    limit: int = 50,
    offset: int = 0,
):
    """List inbox messages with filters."""
    qs = InboxMessage.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if platform:
        qs = qs.filter(platform=platform)
    if status:
        qs = qs.filter(status=status)
    if type:
        qs = qs.filter(type=type)
    if assigned_to:
        qs = qs.filter(assigned_to=assigned_to)
    qs = qs.order_by("-received_at")[offset : offset + limit]
    return [_msg_to_dict(m) for m in qs]


@router.get("/messages/{message_id}", response=MessageOut, tags=["SM Inbox"])
def get_message(request, message_id: str):
    """Get a single inbox message."""
    msg = get_object_or_404(InboxMessage, id=message_id)
    return _msg_to_dict(msg)


@router.post("/messages", response=MessageOut, tags=["SM Inbox"])
def create_message(request, payload: MessageIn):
    """Create a new inbox message."""
    data = payload.dict()
    data["tenant_id"] = getattr(request, "tenant_id", "default")
    data["received_at"] = data.get("received_at") or datetime.now().isoformat()
    msg = InboxMessage.objects.create(**data)
    return _msg_to_dict(msg)


@router.patch("/messages/{message_id}/status", response=dict, tags=["SM Inbox"])
def update_status(request, message_id: str, status: str):
    """Update message status."""
    msg = get_object_or_404(InboxMessage, id=message_id)
    msg.status = status
    msg.save(update_fields=["status"])
    return {"status": "ok", "message_id": message_id, "new_status": status}


@router.post("/messages/{message_id}/reply", response=dict, tags=["SM Inbox"])
def reply_message(request, message_id: str, payload: ReplyIn):
    """Reply to an inbox message."""
    msg = get_object_or_404(InboxMessage, id=message_id)
    now = datetime.now()
    from django.utils import timezone

    now = timezone.now()
    msg.status = "replied"
    msg.replied_at = now
    if msg.received_at:
        delta = now - msg.received_at
        msg.response_time_minutes = int(delta.total_seconds() / 60)
    msg.save(update_fields=["status", "replied_at", "response_time_minutes"])
    return {
        "status": "ok",
        "message_id": message_id,
        "replied_at": now.isoformat(),
        "response_time_minutes": msg.response_time_minutes,
    }


@router.post("/messages/{message_id}/assign", response=dict, tags=["SM Inbox"])
def assign_message(request, message_id: str, payload: AssignIn):
    """Assign an inbox message."""
    msg = get_object_or_404(InboxMessage, id=message_id)
    msg.assigned_to = payload.assigned_to
    msg.assignment_reason = payload.assignment_reason
    msg.save(update_fields=["assigned_to", "assignment_reason"])
    return {"status": "ok", "message_id": message_id, "assigned_to": payload.assigned_to}


@router.get("/messages/{message_id}/thread", response=list[MessageOut], tags=["SM Inbox"])
def get_thread(request, message_id: str):
    """Get all messages in a thread."""
    msg = get_object_or_404(InboxMessage, id=message_id)
    if msg.thread_id:
        qs = InboxMessage.objects.filter(thread_id=msg.thread_id).order_by("received_at")
    else:
        qs = InboxMessage.objects.filter(id=message_id)
    return [_msg_to_dict(m) for m in qs]


@router.post("/messages/bulk-status", response=dict, tags=["SM Inbox"])
def bulk_update_status(request, payload: BulkStatusIn):
    """Bulk update message statuses."""
    updated = InboxMessage.objects.filter(id__in=payload.ids).update(status=payload.status)
    return {"status": "ok", "updated": updated}


@router.post("/aggregate", response=dict, tags=["SM Inbox"])
def trigger_aggregate(request, tenant_id: str = ""):
    """Trigger message aggregation from all platforms."""
    result = aggregate_messages(
        tenant_id=tenant_id or getattr(request, "tenant_id", "default"),
        platform_messages={},
    )
    return result


def _msg_to_dict(msg: InboxMessage) -> dict[str, Any]:
    """Convert InboxMessage to response dict."""
    return {
        "id": str(msg.id),
        "platform": msg.platform,
        "type": msg.type,
        "author_name": msg.author_name,
        "author_avatar": msg.author_avatar,
        "text": msg.text,
        "status": msg.status,
        "sentiment": msg.sentiment,
        "sentiment_score": float(msg.sentiment_score) if msg.sentiment_score else 0,
        "spam_score": float(msg.spam_score) if msg.spam_score else 0,
        "assigned_to": msg.assigned_to,
        "replied_at": msg.replied_at.isoformat() if msg.replied_at else None,
        "response_time_minutes": msg.response_time_minutes,
        "received_at": msg.received_at.isoformat(),
        "created_at": msg.created_at.isoformat(),
    }
