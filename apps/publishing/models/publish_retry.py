"""PublishRetry model — tracks retry attempts with exponential backoff.

Stores each retry attempt with error classification, delay calculation,
and escalation tracking for failed publish operations.
"""

from __future__ import annotations

import random
from typing import Any

from django.db import models

from apps.core.models import TimeStampedModel, UUIDModel


class PublishRetry(UUIDModel, TimeStampedModel):
    """A retry record for a failed publish attempt.

    Attributes:
        scheduled_post: FK to scheduled post.
        attempt_number: Which retry attempt this is.
        error_type: Classified error type.
        error_message: Full error message.
        platform_response_status: HTTP status from platform.
        platform_response_body: Response body from platform.
        delay_seconds: Calculated delay before retry.
        retried_at: When the retry was executed.
        successful: Whether the retry succeeded.
    """

    # Error classification
    class ErrorType(models.TextChoices):
        RATE_LIMIT = "rate_limit", "Rate Limit"
        SERVER_ERROR = "server_error", "Server Error"
        TIMEOUT = "timeout", "Timeout"
        AUTH_EXPIRED = "auth_expired", "Auth Expired"
        NETWORK = "network", "Network Error"
        INVALID_CREDENTIALS = "invalid_credentials", "Invalid Credentials"
        CONTENT_REJECTED = "content_rejected", "Content Rejected"
        ACCOUNT_SUSPENDED = "account_suspended", "Account Suspended"
        QUOTA_EXCEEDED = "quota_exceeded", "Quota Exceeded"
        UNKNOWN = "unknown", "Unknown"

    scheduled_post = models.ForeignKey(
        "ScheduledPost",
        on_delete=models.CASCADE,
        related_name="retries",
        db_index=True,
    )
    attempt_number = models.PositiveIntegerField(
        default=1,
        db_index=True,
        help_text="Retry attempt number",
    )
    error_type = models.CharField(
        max_length=32,
        choices=ErrorType.choices,
        db_index=True,
        help_text="Classified error type",
    )
    error_message = models.TextField(help_text="Full error message")
    platform_response_status = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="HTTP status from platform",
    )
    platform_response_body = models.TextField(
        blank=True,
        help_text="Response body from platform",
    )
    delay_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Calculated delay before retry",
    )
    retried_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When retry was executed",
    )
    successful = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether retry succeeded",
    )

    class Meta:
        db_table = "voyager_publish_retry"
        verbose_name = "Publish Retry"
        verbose_name_plural = "Publish Retries"
        ordering = ["scheduled_post", "attempt_number"]
        indexes = [
            models.Index(fields=["scheduled_post", "attempt_number"]),
            models.Index(fields=["error_type", "created_at"]),
            models.Index(fields=["successful", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Retry {self.attempt_number} for {self.scheduled_post_id} ({self.error_type})"

    @classmethod
    def classify_error(cls, error_code: str) -> dict[str, Any]:
        """Classify an error as retryable or permanent.

        Args:
            error_code: The error code from the platform.

        Returns:
            Dict with retryable flag and classified error type.
        """
        retryable = [
            cls.ErrorType.RATE_LIMIT,
            cls.ErrorType.SERVER_ERROR,
            cls.ErrorType.TIMEOUT,
            cls.ErrorType.NETWORK,
        ]
        permanent = [
            cls.ErrorType.INVALID_CREDENTIALS,
            cls.ErrorType.CONTENT_REJECTED,
            cls.ErrorType.ACCOUNT_SUSPENDED,
            cls.ErrorType.QUOTA_EXCEEDED,
        ]

        if error_code in retryable:
            return {"retryable": True, "type": error_code}
        if error_code in permanent:
            return {"retryable": False, "type": error_code}
        # Unknown: retry up to 3 times
        return {"retryable": True, "type": cls.ErrorType.UNKNOWN}

    @classmethod
    def calculate_delay(cls, attempt_number: int, error_type: str) -> int:
        """Calculate retry delay with exponential backoff and jitter.

        Args:
            attempt_number: 1-based attempt number.
            error_type: Classified error type.

        Returns:
            Delay in seconds (capped at 3600).
        """
        base_delays = {
            cls.ErrorType.RATE_LIMIT: 300,
            cls.ErrorType.SERVER_ERROR: 60,
            cls.ErrorType.TIMEOUT: 120,
            cls.ErrorType.AUTH_EXPIRED: 0,
            cls.ErrorType.NETWORK: 30,
            cls.ErrorType.UNKNOWN: 60,
        }
        base = base_delays.get(error_type, 60)

        delay = base * (2 ** (attempt_number - 1))
        jitter = random.uniform(0, delay * 0.1)  # 10% jitter
        delay = int(delay + jitter)

        return min(delay, 3600)

    @classmethod
    def log_attempt(
        cls,
        scheduled_post_id: str,
        attempt_number: int,
        error_type: str,
        error_message: str,
        response_status: int | None = None,
        response_body: str = "",
    ) -> PublishRetry:
        """Create a retry record with calculated delay.

        Args:
            scheduled_post_id: UUID of the scheduled post.
            attempt_number: Which attempt.
            error_type: Classified error type.
            error_message: Full error message.
            response_status: HTTP status code.
            response_body: Response body.

        Returns:
            Created PublishRetry instance.
        """
        delay = cls.calculate_delay(attempt_number, error_type)
        return cls.objects.create(
            scheduled_post_id=scheduled_post_id,
            attempt_number=attempt_number,
            error_type=error_type,
            error_message=error_message,
            platform_response_status=response_status,
            platform_response_body=response_body,
            delay_seconds=delay,
        )
