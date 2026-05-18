"""Post CRUD views for ScheduledPost management."""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

from ..models import ContentCalendar, PublishQueue, ScheduledPost
from ..services.scheduler import find_optimal_slot

router = Router(auth=VoyagerKeycloakBearer())


# ---------------------------------------------------------------------------
# Request/Response schemas
# ---------------------------------------------------------------------------


class CreatePostIn:
    """Input schema for creating a scheduled post."""

    platform: str
    account_id: str
    caption: str = ""
    hashtags: list[str] = []
    media_urls: list[str] = []
    link: str = ""
    alt_text: str = ""
    first_comment: str = ""
    scheduled_at: str = ""
    timezone: str = "UTC"
    publish_type: str = "feed"
    priority: int = 3
    content_id: str | None = None
    campaign_id: str | None = None
    approval_workflow_id: str | None = None
    tags: list[str] = []
    location_json: dict[str, Any] | None = None


class UpdatePostIn:
    """Input schema for updating a scheduled post."""

    caption: str | None = None
    hashtags: list[str] | None = None
    media_urls: list[str] | None = None
    link: str | None = None
    alt_text: str | None = None
    first_comment: str | None = None
    scheduled_at: str | None = None
    timezone: str | None = None
    publish_type: str | None = None
    priority: int | None = None
    status: str | None = None
    tags: list[str] | None = None


class PostOut:
    """Output schema for a scheduled post."""

    id: str
    platform: str
    account_id: str
    caption: str
    hashtags: list[str]
    media_urls: list[str]
    link: str
    alt_text: str
    scheduled_at: str
    timezone: str
    status: str
    priority: int
    publish_type: str
    approval_status: str
    platform_post_id: str
    publish_attempts: int
    created_at: str
    updated_at: str


class ListPostsOut:
    """Output schema for listing posts."""

    count: int
    posts: list[PostOut]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/posts", response={201: PostOut}, tags=["Publishing Posts"])
def create_post(request, payload: CreatePostIn) -> dict[str, Any]:
    """Create a new scheduled post."""
    tenant_id = getattr(request, "tenant_id", "default")
    user_id = getattr(request, "user_id", "anonymous")

    from django.utils.dateparse import parse_datetime

    scheduled_dt = parse_datetime(payload.scheduled_at)
    if not scheduled_dt:
        scheduled_dt = __import__("django.utils.timezone").utils.timezone.now()

    post = ScheduledPost.objects.create(
        tenant_id=tenant_id,
        platform=payload.platform,
        account_id=payload.account_id,
        caption=payload.caption,
        hashtags=payload.hashtags,
        media_urls=payload.media_urls,
        link=payload.link,
        alt_text=payload.alt_text,
        first_comment=payload.first_comment,
        scheduled_at=scheduled_dt,
        timezone=payload.timezone,
        publish_type=payload.publish_type,
        priority=payload.priority,
        content_id=payload.content_id,
        campaign_id=payload.campaign_id,
        approval_workflow_id=payload.approval_workflow_id,
        tags=payload.tags,
        location_json=payload.location_json or {},
        created_by=user_id,
        status=ScheduledPost.Status.SCHEDULED,
    )

    # Create calendar entry
    ContentCalendar.objects.create(
        tenant_id=tenant_id,
        scheduled_post=post,
        calendar_view=ContentCalendar.CalendarView.MONTH,
    )

    # Create queue entry
    PublishQueue.objects.get_or_create(
        scheduled_post=post,
        defaults={"queue_priority": payload.priority},
    )

    return 201, _post_to_dict(post)


@router.get("/posts", response=ListPostsOut, tags=["Publishing Posts"])
def list_posts(
    request,
    platform: str = "",
    status: str = "",
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """List scheduled posts with optional filtering."""
    tenant_id = getattr(request, "tenant_id", "default")
    qs = ScheduledPost.objects.filter(tenant_id=tenant_id)

    if platform:
        qs = qs.filter(platform=platform)
    if status:
        qs = qs.filter(status=status)

    total = qs.count()
    posts = qs.order_by("-scheduled_at")[offset : offset + limit]

    return {
        "count": total,
        "posts": [_post_to_dict(p) for p in posts],
    }


@router.get("/posts/{post_id}", response=PostOut, tags=["Publishing Posts"])
def get_post(request, post_id: str) -> dict[str, Any]:
    """Get a single scheduled post."""
    tenant_id = getattr(request, "tenant_id", "default")
    post = get_object_or_404(ScheduledPost, id=post_id, tenant_id=tenant_id)
    return _post_to_dict(post)


@router.put("/posts/{post_id}", response=PostOut, tags=["Publishing Posts"])
def update_post(request, post_id: str, payload: UpdatePostIn) -> dict[str, Any]:
    """Update a scheduled post."""
    tenant_id = getattr(request, "tenant_id", "default")
    post = get_object_or_404(ScheduledPost, id=post_id, tenant_id=tenant_id)

    update_fields: list[str] = []
    if payload.caption is not None:
        post.caption = payload.caption
        update_fields.append("caption")
    if payload.hashtags is not None:
        post.hashtags = payload.hashtags
        update_fields.append("hashtags")
    if payload.media_urls is not None:
        post.media_urls = payload.media_urls
        update_fields.append("media_urls")
    if payload.link is not None:
        post.link = payload.link
        update_fields.append("link")
    if payload.alt_text is not None:
        post.alt_text = payload.alt_text
        update_fields.append("alt_text")
    if payload.first_comment is not None:
        post.first_comment = payload.first_comment
        update_fields.append("first_comment")
    if payload.scheduled_at is not None:
        from django.utils.dateparse import parse_datetime

        dt = parse_datetime(payload.scheduled_at)
        if dt:
            post.scheduled_at = dt
            update_fields.append("scheduled_at")
    if payload.timezone is not None:
        post.timezone = payload.timezone
        update_fields.append("timezone")
    if payload.publish_type is not None:
        post.publish_type = payload.publish_type
        update_fields.append("publish_type")
    if payload.priority is not None:
        post.priority = payload.priority
        update_fields.append("priority")
    if payload.status is not None:
        post.status = payload.status
        update_fields.append("status")
    if payload.tags is not None:
        post.tags = payload.tags
        update_fields.append("tags")

    if update_fields:
        update_fields.append("updated_at")
        post.save(update_fields=update_fields)

    return _post_to_dict(post)


@router.delete("/posts/{post_id}", response={204: None}, tags=["Publishing Posts"])
def delete_post(request, post_id: str) -> tuple[int, None]:
    """Soft-delete (cancel) a scheduled post."""
    tenant_id = getattr(request, "tenant_id", "default")
    post = get_object_or_404(ScheduledPost, id=post_id, tenant_id=tenant_id)
    post.status = ScheduledPost.Status.CANCELLED
    post.save(update_fields=["status"])
    # Remove from queue
    PublishQueue.objects.filter(scheduled_post=post).delete()
    return 204, None


@router.post("/posts/{post_id}/optimal-slot", response=dict, tags=["Publishing Posts"])
def get_optimal_slot(request, post_id: str) -> dict[str, Any]:
    """Find optimal publishing slot for a post."""
    tenant_id = getattr(request, "tenant_id", "default")
    post = get_object_or_404(ScheduledPost, id=post_id, tenant_id=tenant_id)
    result = find_optimal_slot(
        tenant_id=tenant_id,
        platform=post.platform,
        account_id=str(post.account_id),
        preferred_date=post.scheduled_at,
    )
    return result


def _post_to_dict(post: ScheduledPost) -> dict[str, Any]:
    """Convert a ScheduledPost to a dict."""
    return {
        "id": str(post.id),
        "platform": post.platform,
        "account_id": str(post.account_id),
        "caption": post.caption or "",
        "hashtags": list(post.hashtags) if post.hashtags else [],
        "media_urls": list(post.media_urls) if post.media_urls else [],
        "link": post.link or "",
        "alt_text": post.alt_text or "",
        "scheduled_at": post.scheduled_at.isoformat(),
        "timezone": post.timezone,
        "status": post.status,
        "priority": post.priority,
        "publish_type": post.publish_type,
        "approval_status": post.approval_status,
        "platform_post_id": post.platform_post_id or "",
        "publish_attempts": post.publish_attempts,
        "created_at": post.created_at.isoformat(),
        "updated_at": post.updated_at.isoformat(),
    }
