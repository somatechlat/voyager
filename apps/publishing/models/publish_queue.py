"""PublishQueue model — manages content publishing queues.

Tracks queue priority, frequency limits, overflow handling,
retry count, and error logs for each scheduled post in queue.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from .base import TimeStampedModel, UUIDModel


class PublishQueue(UUIDModel, TimeStampedModel):
    """An entry in the publishing queue for a scheduled post.

    Attributes:
        scheduled_post: FK to the scheduled post.
        queue_priority: Lower = higher priority (0=urgent, 3=low).
        retry_count: Number of retry attempts.
        next_retry_at: When to attempt next retry.
        error_log: JSON array of error entries.
        overflow_reason: Why this was overflowed (frequency_limit, etc.).
        overflowed_at: When overflow happened.
        processed_at: When successfully processed.
    """

    class OverflowReason(models.TextChoices):
        FREQUENCY_LIMIT = "frequency_limit", "Frequency Limit"
        BLACKOUT_WINDOW = "blackout_window", "Blackout Window"
        RATE_LIMIT = "rate_limit", "Platform Rate Limit"
        QUEUE_FULL = "queue_full", "Queue Full"
        MANUAL = "manual", "Manual Overflow"

    scheduled_post = models.OneToOneField(
        "ScheduledPost",
        on_delete=models.CASCADE,
        related_name="queue_entry",
        db_index=True,
    )
    queue_priority = models.PositiveSmallIntegerField(
        default=3, db_index=True,
        help_text="0=urgent, 1=high, 2=medium, 3=low",
    )
    retry_count = models.PositiveIntegerField(default=0)
    next_retry_at = models.DateTimeField(
        null=True, blank=True, db_index=True,
        help_text="When to attempt next retry",
    )
    error_log = models.JSONField(
        default=list, blank=True,
        help_text="List of error entries: [{timestamp, error, attempt}]",
    )
    overflow_reason = models.CharField(
        max_length=32, choices=OverflowReason.choices,
        blank=True, help_text="Why this post was overflowed",
    )
    overflowed_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When overflow happened",
    )
    processed_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When successfully processed",
    )

    class Meta:
        db_table = "voyager_publish_queue"
        verbose_name = "Publish Queue Entry"
        verbose_name_plural = "Publish Queue Entries"
        ordering = ["queue_priority", "next_retry_at"]
        indexes = [
            models.Index(fields=["queue_priority", "next_retry_at"]),
            models.Index(fields=["scheduled_post", "processed_at"]),
        ]

    def __str__(self) -> str:
        return f"Queue {self.scheduled_post_id} (pri={self.queue_priority})"

    def log_error(self, error: str) -> None:
        """Append an error entry to the error log."""
        entry = {
            "timestamp": timezone.now().isoformat(),
            "error": error,
            "attempt": self.retry_count,
        }
        log = list(self.error_log) if self.error_log else []
        log.append(entry)
        self.error_log = log[-50:]  # Keep last 50
        self.save(update_fields=["error_log"])

    def mark_processed(self) -> None:
        """Mark queue entry as successfully processed."""
        self.processed_at = timezone.now()
        self.next_retry_at = None
        self.save(update_fields=["processed_at", "next_retry_at"])

    def schedule_retry(self, retry_at: timezone.datetime) -> None:
        """Schedule next retry attempt."""
        self.retry_count += 1
        self.next_retry_at = retry_at
        self.save(update_fields=["retry_count", "next_retry_at"])

    def mark_overflowed(self, reason: str) -> None:
        """Mark as overflowed with reason."""
        self.overflow_reason = reason
        self.overflowed_at = timezone.now()
        self.save(update_fields=["overflow_reason", "overflowed_at"])

    @classmethod
    def get_pending(cls) -> models.QuerySet:
        """Get pending queue entries ordered by priority."""
        return cls.objects.filter(
            processed_at__isnull=True,
        ).select_related("scheduled_post").order_by("queue_priority", "next_retry_at")
