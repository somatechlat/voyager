"""Retry service — handles failed publish attempts with exponential backoff.

Classifies errors, calculates retry delays, and manages escalation
matrix for persistent failures.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.utils import timezone

from ..models import PublishQueue, PublishRetry, ScheduledPost

logger = logging.getLogger(__name__)


# Escalation matrix: attempt → action
ESCALATION_MATRIX: dict[int, dict[str, str]] = {
    1: {"action": "auto_retry", "notify": "none"},
    2: {"action": "auto_retry", "notify": "none"},
    3: {"action": "auto_retry", "notify": "creator"},
    4: {"action": "auto_retry", "notify": "creator"},
    5: {"action": "auto_retry", "notify": "team_lead"},
    6: {"action": "auto_retry", "notify": "team_lead"},
    7: {"action": "manual_intervention", "notify": "admin"},
    8: {"action": "manual_intervention", "notify": "admin"},
    9: {"action": "manual_intervention", "notify": "admin"},
    10: {"action": "permanent_failure", "notify": "all"},
}

RETRYABLE_ERRORS: list[str] = [
    PublishRetry.ErrorType.RATE_LIMIT,
    PublishRetry.ErrorType.SERVER_ERROR,
    PublishRetry.ErrorType.TIMEOUT,
    PublishRetry.ErrorType.NETWORK,
]

PERMANENT_ERRORS: list[str] = [
    PublishRetry.ErrorType.INVALID_CREDENTIALS,
    PublishRetry.ErrorType.CONTENT_REJECTED,
    PublishRetry.ErrorType.ACCOUNT_SUSPENDED,
    PublishRetry.ErrorType.QUOTA_EXCEEDED,
]


def classify_error(
    error_message: str,
    status_code: int | None = None,
) -> dict[str, Any]:
    """Classify an error as retryable or permanent.

    Args:
        error_message: Error message from platform.
        status_code: HTTP status code if available.

    Returns:
        Dict with retryable flag, error_type, and error_code.
    """
    msg = error_message.lower()

    # HTTP status based classification
    if status_code:
        if status_code == 429:
            return {"retryable": True, "error_type": PublishRetry.ErrorType.RATE_LIMIT}
        if status_code in (500, 502, 503, 504):
            return {"retryable": True, "error_type": PublishRetry.ErrorType.SERVER_ERROR}
        if status_code in (401, 403):
            if "suspended" in msg:
                return {"retryable": False, "error_type": PublishRetry.ErrorType.ACCOUNT_SUSPENDED}
            return {"retryable": False, "error_type": PublishRetry.ErrorType.INVALID_CREDENTIALS}
        if status_code == 400:
            if "rejected" in msg or "invalid" in msg:
                return {"retryable": False, "error_type": PublishRetry.ErrorType.CONTENT_REJECTED}

    # Message based classification
    if any(kw in msg for kw in ("rate limit", "too many requests", "throttled")):
        return {"retryable": True, "error_type": PublishRetry.ErrorType.RATE_LIMIT}
    if any(kw in msg for kw in ("timeout", "timed out")):
        return {"retryable": True, "error_type": PublishRetry.ErrorType.TIMEOUT}
    if any(kw in msg for kw in ("network", "connection", "unreachable")):
        return {"retryable": True, "error_type": PublishRetry.ErrorType.NETWORK}
    if any(kw in msg for kw in ("unauthorized", "auth expired", "token expired")):
        return {"retryable": True, "error_type": PublishRetry.ErrorType.AUTH_EXPIRED}
    if any(kw in msg for kw in ("suspended", "disabled", "banned")):
        return {"retryable": False, "error_type": PublishRetry.ErrorType.ACCOUNT_SUSPENDED}
    if any(kw in msg for kw in ("quota", "limit exceeded", "overage")):
        return {"retryable": False, "error_type": PublishRetry.ErrorType.QUOTA_EXCEEDED}
    if any(kw in msg for kw in ("rejected", "invalid content", "policy")):
        return {"retryable": False, "error_type": PublishRetry.ErrorType.CONTENT_REJECTED}

    return {"retryable": True, "error_type": PublishRetry.ErrorType.UNKNOWN}


def get_escalation_action(attempt_number: int) -> dict[str, str]:
    """Get escalation action for a given attempt number.

    Args:
        attempt_number: Current attempt number.

    Returns:
        Dict with action and notify targets.
    """
    if attempt_number > 10:
        attempt_number = 10
    return ESCALATION_MATRIX.get(attempt_number, {"action": "permanent_failure", "notify": "all"})


def schedule_retry(
    post: ScheduledPost,
    error_message: str,
    status_code: int | None = None,
) -> dict[str, Any]:
    """Schedule a retry for a failed post.

    Args:
        post: The failed scheduled post.
        error_message: Error from platform.
        status_code: HTTP status code.

    Returns:
        Result dict with retry scheduled, delay, escalation info.
    """
    classification = classify_error(error_message, status_code)
    error_type = classification["error_type"]
    retryable = classification["retryable"]

    # Count existing retries
    existing_retries = PublishRetry.objects.filter(scheduled_post=post).count()
    attempt_number = existing_retries + 1

    # Log the retry
    retry = PublishRetry.log_attempt(
        scheduled_post_id=str(post.id),
        attempt_number=attempt_number,
        error_type=error_type,
        error_message=error_message,
        response_status=status_code,
    )

    if not retryable:
        post.mark_failed(error_message)
        return {
            "retryable": False,
            "error_type": error_type,
            "attempt": attempt_number,
            "action": "permanent_failure",
            "notify": "all",
        }

    # Calculate delay
    delay = PublishRetry.calculate_delay(attempt_number, error_type)
    retry_at = timezone.now() + timedelta(seconds=delay)

    # Get escalation action
    escalation = get_escalation_action(attempt_number)

    # Update queue entry
    queue_entry, _ = PublishQueue.objects.get_or_create(scheduled_post=post)
    queue_entry.schedule_retry(retry_at)

    # Update post status
    post.status = ScheduledPost.Status.SCHEDULED
    post.save(update_fields=["status"])

    logger.info(
        "Retry %s for post %s: type=%s delay=%ss action=%s",
        attempt_number,
        post.id,
        error_type,
        delay,
        escalation["action"],
    )

    return {
        "retryable": True,
        "error_type": error_type,
        "attempt": attempt_number,
        "delay_seconds": delay,
        "retry_at": retry_at.isoformat(),
        "action": escalation["action"],
        "notify": escalation["notify"],
    }


def process_failed_posts() -> dict[str, int]:
    """Process all failed posts and schedule retries.

    Returns:
        Dict with processed and retried counts.
    """
    failed_posts = ScheduledPost.objects.filter(
        status=ScheduledPost.Status.FAILED,
        publish_attempts__lt=10,
    )

    processed = 0
    retried = 0

    for post in failed_posts[:50]:
        try:
            result = schedule_retry(post, post.last_error)
            processed += 1
            if result["retryable"]:
                retried += 1
        except Exception:
            logger.exception("Error processing failed post %s", post.id)

    return {"processed": processed, "retried": retried}
