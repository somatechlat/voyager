"""Email subscriber management views."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.email_marketing.models.subscriber import EmailSubscriber
from apps.email_marketing.serializers import (
    EmailSubscriberCreateSchema,
    EmailSubscriberDetailSchema,
    EmailSubscriberListSchema,
    EmailSubscriberUpdateSchema,
    SubscriberBulkSchema,
    SubscriberSuppressSchema,
    SubscriberTagSchema,
)

logger = logging.getLogger(__name__)

router = Router()


@router.get("/", response=list[EmailSubscriberListSchema])
def list_subscribers(
    request,
    tenant_id: str = "",
    status: str = "",
    search: str = "",
    tag: str = "",
    limit: int = 50,
    offset: int = 0,
) -> list[EmailSubscriber]:
    """List email subscribers with optional filtering.

    Args:
        request: HTTP request.
        tenant_id: Filter by tenant.
        status: Filter by status.
        search: Search in email, first_name, last_name.
        tag: Filter by tag.
        limit: Page size.
        offset: Pagination offset.

    Returns:
        List of subscribers.
    """
    qs = EmailSubscriber.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if status:
        qs = qs.filter(status=status)
    if tag:
        qs = qs.filter(tags__contains=[tag])
    if search:
        qs = qs.filter(
            email__icontains=search
        ) | qs.filter(
            first_name__icontains=search
        ) | qs.filter(
            last_name__icontains=search
        )
    return list(qs.order_by("-subscribed_at")[offset : offset + limit])


@router.post("/", response=EmailSubscriberDetailSchema)
def create_subscriber(
    request,
    payload: EmailSubscriberCreateSchema,
) -> EmailSubscriber:
    """Create a new email subscriber.

    Args:
        request: HTTP request.
        payload: Subscriber creation data.

    Returns:
        Created subscriber.
    """
    data = payload.dict()
    subscriber, created = EmailSubscriber.objects.get_or_create(
        tenant_id=data["tenant_id"],
        email=data["email"],
        defaults=data,
    )
    if created:
        logger.info("Subscriber %s created for tenant %s", subscriber.id, subscriber.tenant_id)
    return subscriber


@router.get("/{subscriber_id}", response=EmailSubscriberDetailSchema)
def get_subscriber(
    request,
    subscriber_id: int,
) -> EmailSubscriber:
    """Get a single email subscriber.

    Args:
        request: HTTP request.
        subscriber_id: Subscriber primary key.

    Returns:
        Email subscriber.
    """
    return get_object_or_404(EmailSubscriber, id=subscriber_id)


@router.put("/{subscriber_id}", response=EmailSubscriberDetailSchema)
def update_subscriber(
    request,
    subscriber_id: int,
    payload: EmailSubscriberUpdateSchema,
) -> EmailSubscriber:
    """Update an email subscriber.

    Args:
        request: HTTP request.
        subscriber_id: Subscriber primary key.
        payload: Update data.

    Returns:
        Updated subscriber.
    """
    subscriber = get_object_or_404(EmailSubscriber, id=subscriber_id)
    data = payload.dict(exclude_unset=True)
    for attr, val in data.items():
        setattr(subscriber, attr, val)
    subscriber.save()
    return subscriber


@router.delete("/{subscriber_id}")
def delete_subscriber(
    request,
    subscriber_id: int,
) -> dict[str, bool]:
    """Delete an email subscriber.

    Args:
        request: HTTP request.
        subscriber_id: Subscriber primary key.

    Returns:
        Success dict.
    """
    subscriber = get_object_or_404(EmailSubscriber, id=subscriber_id)
    subscriber.delete()
    return {"success": True}


@router.post("/bulk")
def bulk_create_subscribers(
    request,
    payload: SubscriberBulkSchema,
) -> dict[str, Any]:
    """Bulk create or update subscribers.

    Args:
        request: HTTP request.
        payload: Bulk subscriber data.

    Returns:
        Bulk operation result.
    """
    created_count = 0
    updated_count = 0
    for sub_data in payload.subscribers:
        sub_dict = dict(sub_data)
        sub, created = EmailSubscriber.objects.get_or_create(
            tenant_id=sub_dict["tenant_id"],
            email=sub_dict["email"],
            defaults=sub_dict,
        )
        if created:
            created_count += 1
        else:
            for attr, val in sub_dict.items():
                if attr not in ("tenant_id", "email"):
                    setattr(sub, attr, val)
            sub.save()
            updated_count += 1
    return {"created": created_count, "updated": updated_count}


@router.post("/{subscriber_id}/tags")
def update_tags(
    request,
    subscriber_id: int,
    payload: SubscriberTagSchema,
) -> dict[str, Any]:
    """Update subscriber tags.

    Args:
        request: HTTP request.
        subscriber_id: Subscriber primary key.
        payload: Tags data.

    Returns:
        Updated tags.
    """
    subscriber = get_object_or_404(EmailSubscriber, id=subscriber_id)
    if payload.operation == "add":
        current = set(subscriber.tags or [])
        current.update(payload.tags)
        subscriber.tags = list(current)
    elif payload.operation == "remove":
        current = set(subscriber.tags or [])
        current.difference_update(payload.tags)
        subscriber.tags = list(current)
    else:
        subscriber.tags = payload.tags
    subscriber.save(update_fields=["tags"])
    return {"subscriber_id": str(subscriber.id), "tags": subscriber.tags}


@router.post("/{subscriber_id}/suppress")
def suppress_subscriber(
    request,
    subscriber_id: int,
    payload: SubscriberSuppressSchema,
) -> dict[str, Any]:
    """Suppress a subscriber (bounce, complaint, or manual).

    Args:
        request: HTTP request.
        subscriber_id: Subscriber primary key.
        payload: Suppression data.

    Returns:
        Suppression result.
    """
    subscriber = get_object_or_404(EmailSubscriber, id=subscriber_id)
    subscriber.status = payload.reason
    if payload.reason == EmailSubscriber.Status.UNSUBSCRIBED:
        subscriber.unsubscribed_at = datetime.now(UTC)
    subscriber.save(update_fields=["status", "unsubscribed_at"])
    logger.info("Subscriber %s suppressed: %s", subscriber.id, payload.reason)
    return {"success": True, "subscriber_id": str(subscriber.id), "status": subscriber.status}


@router.get("/{subscriber_id}/rfm")
def get_rfm_score(
    request,
    subscriber_id: int,
) -> dict[str, Any]:
    """Get RFM score for a subscriber.

    Args:
        request: HTTP request.
        subscriber_id: Subscriber primary key.

    Returns:
        RFM score breakdown.
    """
    from apps.email_marketing.services.segments import calculate_rfm_scores

    subscriber = get_object_or_404(EmailSubscriber, id=subscriber_id)
    scores = calculate_rfm_scores(subscriber)
    return {
        "subscriber_id": str(subscriber.id),
        "email": subscriber.email,
        "rfm_score": subscriber.rfm_score,
        **scores,
    }
