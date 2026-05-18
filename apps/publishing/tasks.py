"""Celery tasks for the Publishing module.

Handles scheduled post publishing, recurring post processing,
approval timeout checking, and retry management for failed posts.

Tasks are routed to the ``publishing`` queue via
``voyager_project.celery.app.conf.task_routes``.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from django.utils import timezone

from apps.publishing.models import ScheduledPost

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def publish_due_posts(self) -> dict[str, Any]:
    """Publish all posts whose ``scheduled_at`` timestamp has passed.

    Called by the beat scheduler every 60 seconds. Iterates over
    :class:`apps.publishing.models.ScheduledPost` records with
    ``status='scheduled'`` and ``scheduled_at <= now()`` and dispatches
    each to the appropriate platform.

    Returns:
        Summary dict with ``published``, ``failed``, ``skipped`` counts.
    """
    logger.info("Task started: %s", self.name)

    due_posts = ScheduledPost.objects.filter(
        status=ScheduledPost.Status.SCHEDULED,
        scheduled_at__lte=timezone.now(),
        publish_attempts__lt=10,
    ).select_related()[:50]

    published = 0
    failed = 0
    skipped = 0

    for post in due_posts:
        if not post.can_publish():
            skipped += 1
            logger.info("Post %s skipped (cannot publish)", post.id)
            continue

        try:
            from apps.publishing.services.publisher import publish_to_platforms
            result = publish_to_platforms(post)
            if result.get("success"):
                published += 1
                logger.info("Post %s published successfully", post.id)
            else:
                failed += 1
                logger.warning(
                    "Post %s failed: %s (type=%s, retryable=%s)",
                    post.id, result.get("error"), result.get("error_type"),
                    result.get("retryable"),
                )
        except Exception:
            failed += 1
            logger.exception("Error publishing post %s", post.id)

    result: dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "published": published,
        "failed": failed,
        "skipped": skipped,
    }
    logger.info("Task completed: %s -- %r", self.name, result)
    return result


@shared_task(bind=True, max_retries=3)
def process_recurring_posts(self) -> dict[str, Any]:
    """Generate new instances of recurring post series.

    Called by the beat scheduler every hour. Looks for
    :class:`apps.publishing.models.RecurringPost` definitions whose
    next occurrence is due and creates a new
    :class:`apps.publishing.models.ScheduledPost` from the template.

    Returns:
        Summary dict with ``created`` count.
    """
    logger.info("Task started: %s", self.name)

    from apps.publishing.services.recurring import process_all_recurring

    result_data = process_all_recurring()

    result: dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "created": result_data.get("created", 0),
    }
    logger.info("Task completed: %s -- %r", self.name, result)
    return result


@shared_task(bind=True, max_retries=3)
def retry_failed_posts(self) -> dict[str, Any]:
    """Retry failed posts with exponential backoff.

    Called by the beat scheduler every 5 minutes. Processes posts
    with status 'failed' and schedules retries based on error
    classification and escalation matrix.

    Returns:
        Summary dict with ``processed`` and ``retried`` counts.
    """
    logger.info("Task started: %s", self.name)

    from apps.publishing.services.retry import process_failed_posts

    result_data = process_failed_posts()

    result: dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "processed": result_data.get("processed", 0),
        "retried": result_data.get("retried", 0),
    }
    logger.info("Task completed: %s -- %r", self.name, result)
    return result


@shared_task(bind=True, max_retries=3)
def check_approval_timeouts(self) -> dict[str, Any]:
    """Check approval instances for timeouts and escalate.

    Called by the beat scheduler every 15 minutes. Scans pending
    approval instances for overdue steps and triggers escalation
    or auto-approval based on workflow configuration.

    Returns:
        Summary dict with ``escalated`` and ``auto_approved`` counts.
    """
    logger.info("Task started: %s", self.name)

    from apps.publishing.services.approval import check_timeouts

    result_data = check_timeouts()

    result: dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "escalated": result_data.get("escalated", 0),
        "auto_approved": result_data.get("auto_approved", 0),
    }
    logger.info("Task completed: %s -- %r", self.name, result)
    return result


@shared_task(bind=True, max_retries=3)
def process_queue(self) -> dict[str, Any]:
    """Process the publishing queue.

    Called by the beat scheduler every 30 seconds. Processes pending
    queue entries, handling overflow and publishing.

    Returns:
        Summary dict with ``processed`` and ``failed`` counts.
    """
    logger.info("Task started: %s", self.name)

    from apps.publishing.services.queue import QueueManager

    # Process for all tenants with pending queue entries
    tenant_ids = (
        ScheduledPost.objects.filter(
            status=ScheduledPost.Status.SCHEDULED,
            queue_entry__processed_at__isnull=True,
        )
        .values_list("tenant_id", flat=True)
        .distinct()
    )

    total_processed = 0
    total_failed = 0

    for tenant_id in tenant_ids:
        try:
            manager = QueueManager(tenant_id)
            result = manager.process_queue()
            total_processed += result.get("processed", 0)
            total_failed += result.get("failed", 0)
        except Exception:
            logger.exception("Queue processing error for tenant %s", tenant_id)

    result: dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "processed": total_processed,
        "failed": total_failed,
    }
    logger.info("Task completed: %s -- %r", self.name, result)
    return result


@shared_task(bind=True, max_retries=3)
def publish_post(
    self,
    post_id: str,
    platform: str,
    content: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Publish a single post to the specified platform.

    Args:
        post_id: UUID of the ScheduledPost.
        platform: Target platform.
        content: Optional content override.

    Returns:
        Result dict with ``post_id``, ``platform``, ``status``,
        ``external_id``.
    """
    logger.info("Publishing post %s to %s", post_id, platform)

    try:
        post = ScheduledPost.objects.get(id=post_id)
    except ScheduledPost.DoesNotExist:
        return {"success": False, "error": "Post not found", "post_id": post_id}

    from apps.publishing.services.publisher import publish_to_platforms
    result = publish_to_platforms(post)

    return {
        "status": "ok",
        "task": self.name,
        "post_id": post_id,
        "platform": platform,
        "success": result.get("success", False),
        "external_id": result.get("platform_post_id"),
        "error": result.get("error"),
    }
