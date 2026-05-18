"""Queue service — manages publish queue with frequency limits and overflow.

Handles priority queuing, frequency management, and overflow spillover
when content exceeds daily platform limits.
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import models
from django.utils import timezone

from ..models import PublishQueue, ScheduledPost
from .scheduler import PLATFORM_DEFAULTS, get_daily_post_count, get_next_available_slot

logger = logging.getLogger(__name__)


class QueueManager:
    """Manages the publishing queue for a tenant."""

    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id

    def enqueue(self, post: ScheduledPost, priority: int = 3) -> PublishQueue:
        """Add a scheduled post to the publish queue.

        Args:
            post: The scheduled post to enqueue.
            priority: Queue priority (0=urgent, 3=low).

        Returns:
            Created PublishQueue entry.
        """
        entry, created = PublishQueue.objects.get_or_create(
            scheduled_post=post,
            defaults={
                "queue_priority": priority,
            },
        )
        if not created:
            entry.queue_priority = priority
            entry.save(update_fields=["queue_priority"])
        return entry

    def dequeue(self, post_id: str) -> None:
        """Remove a post from the queue.

        Args:
            post_id: UUID of the scheduled post.
        """
        PublishQueue.objects.filter(scheduled_post_id=post_id).delete()

    def get_pending(self) -> models.QuerySet:
        """Get pending queue entries ordered by priority."""
        return PublishQueue.get_pending()

    def check_overflow(
        self,
        post: ScheduledPost,
    ) -> dict[str, Any]:
        """Check if a post would overflow frequency limits.

        Args:
            post: Scheduled post to check.

        Returns:
            Dict with overflow, reason, and next_available_slot.
        """
        platform = post.platform
        account_id = str(post.account_id)
        limits = PLATFORM_DEFAULTS.get(
            platform, {"maxPerDay": 3, "maxPerWeek": 14, "minInterval": 120}
        )

        daily_count = get_daily_post_count(
            self.tenant_id,
            platform,
            account_id,
            post.scheduled_at,
        )

        if daily_count >= limits["maxPerDay"]:
            next_slot = get_next_available_slot(
                self.tenant_id,
                platform,
                account_id,
                post.scheduled_at,
            )
            return {
                "overflow": True,
                "reason": PublishQueue.OverflowReason.FREQUENCY_LIMIT,
                "current_daily": daily_count,
                "max_daily": limits["maxPerDay"],
                "next_available_slot": next_slot.isoformat() if next_slot else None,
            }

        return {"overflow": False}

    def handle_overflow(self, post: ScheduledPost) -> dict[str, Any]:
        """Handle overflow by finding next available slot.

        Args:
            post: Post to handle overflow for.

        Returns:
            Dict with overflow result.
        """
        result = self.check_overflow(post)
        if result["overflow"]:
            # Create queue entry with overflow status
            entry, _ = PublishQueue.objects.get_or_create(scheduled_post=post)
            entry.mark_overflowed(str(result["reason"]))
            logger.info(
                "Post %s overflowed: %s (daily %s/%s)",
                post.id,
                result["reason"],
                result["current_daily"],
                result["max_daily"],
            )
            # Auto-spillover: schedule for next available slot
            if result["next_available_slot"]:
                from datetime import datetime as dt

                next_slot = dt.fromisoformat(result["next_available_slot"])
                post.scheduled_at = next_slot
                post.save(update_fields=["scheduled_at"])
                logger.info("Auto-spillover: post %s rescheduled to %s", post.id, next_slot)
        return result

    def process_queue(self) -> dict[str, Any]:
        """Process pending queue entries.

        Returns:
            Dict with processed and failed counts.
        """
        entries = self.get_pending().filter(
            models.Q(next_retry_at__isnull=True) | models.Q(next_retry_at__lte=timezone.now()),
        )
        processed = 0
        failed = 0

        for entry in entries[:50]:  # Process in batches
            post = entry.scheduled_post
            if not post.can_publish():
                continue
            try:
                # Check overflow
                overflow = self.check_overflow(post)
                if overflow["overflow"]:
                    self.handle_overflow(post)
                    continue

                # Publish
                from .publisher import publish_to_platforms

                result = publish_to_platforms(post)
                if result["success"]:
                    entry.mark_processed()
                    processed += 1
                else:
                    entry.log_error(result.get("error", "Unknown error"))
                    failed += 1
            except Exception as exc:
                logger.exception("Queue processing error for post %s", post.id)
                entry.log_error(str(exc))
                failed += 1

        return {"processed": processed, "failed": failed, "tenant_id": self.tenant_id}

    def get_queue_status(self) -> dict[str, Any]:
        """Get queue status summary.

        Returns:
            Dict with counts per status.
        """
        qs = PublishQueue.objects.filter(
            scheduled_post__tenant_id=self.tenant_id,
        )
        return {
            "total": qs.count(),
            "pending": qs.filter(processed_at__isnull=True).count(),
            "processed": qs.filter(processed_at__isnull=False).count(),
            "overflowed": qs.filter(overflow_reason__isnull=False)
            .exclude(overflow_reason="")
            .count(),
        }
