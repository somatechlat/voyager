"""Bulk import views for CSV/Excel scheduled post imports.

Handles multi-row validation, error reporting, and background processing
for large imports (>100 rows).
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta
from typing import Any

from django.utils import timezone
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

from ..models import ContentCalendar, PublishQueue, ScheduledPost
from ..services.publisher import _PUBLISHER_MAP

logger = logging.getLogger(__name__)

router = Router(auth=VoyagerKeycloakBearer())

# Platform max characters
PLATFORM_MAX_CHARS: dict[str, int] = {
    "instagram": 2200,
    "linkedin": 3000,
    "twitter": 280,
    "tiktok": 2200,
    "youtube": 5000,
    "pinterest": 500,
    "facebook": 2200,
    "threads": 500,
}

VALID_IMAGE_FORMATS = (".jpg", ".jpeg", ".png", ".gif", ".webp")


class BulkImportIn:
    """Input for bulk import."""

    csv_data: str
    dry_run: bool = True


class BulkRowResult:
    """Result for a single CSV row."""

    row: int
    success: bool
    post_id: str | None
    errors: list[str]
    warnings: list[str]


class BulkImportOut:
    """Output for bulk import."""

    valid: bool
    total_rows: int
    valid_rows: int
    error_rows: int
    created: int
    errors: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    dry_run: bool


@router.post("/bulk/import", response=BulkImportOut, tags=["Publishing Bulk"])
def bulk_import(request, payload: BulkImportIn) -> dict[str, Any]:
    """Import scheduled posts from CSV data.

    CSV columns: platform,account_id,content_type,text,image_url,video_url,scheduled_at,timezone,hashtags,link,approval_required
    """
    tenant_id = getattr(request, "tenant_id", "default")
    user_id = getattr(request, "user_id", "anonymous")

    reader = csv.DictReader(io.StringIO(payload.csv_data.strip()))
    rows = list(reader)

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    created = 0

    for idx, row in enumerate(rows, start=2):  # Header is row 1
        row_errors, row_warnings = _validate_row(row, idx)
        errors.extend(row_errors)
        warnings.extend(row_warnings)

        if not row_errors and not payload.dry_run:
            try:
                _create_post_from_row(row, tenant_id, user_id)
                created += 1
            except Exception as exc:
                errors.append({"row": idx, "error": str(exc)})

    valid_rows = len(rows) - len({e.get("row") for e in errors})

    return {
        "valid": len(errors) == 0,
        "total_rows": len(rows),
        "valid_rows": valid_rows,
        "error_rows": len({e.get("row") for e in errors}),
        "created": created,
        "errors": errors,
        "warnings": warnings,
        "dry_run": payload.dry_run,
    }


@router.post("/bulk/validate", response=BulkImportOut, tags=["Publishing Bulk"])
def bulk_validate(request, payload: BulkImportIn) -> dict[str, Any]:
    """Validate CSV data without creating posts."""
    reader = csv.DictReader(io.StringIO(payload.csv_data.strip()))
    rows = list(reader)

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for idx, row in enumerate(rows, start=2):
        row_errors, row_warnings = _validate_row(row, idx)
        errors.extend(row_errors)
        warnings.extend(row_warnings)

    valid_rows = len(rows) - len({e.get("row") for e in errors})

    return {
        "valid": len(errors) == 0,
        "total_rows": len(rows),
        "valid_rows": valid_rows,
        "error_rows": len({e.get("row") for e in errors}),
        "created": 0,
        "errors": errors,
        "warnings": warnings,
        "dry_run": True,
    }


def _validate_row(
    row: dict[str, str], row_num: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate a single CSV row."""
    row_errors: list[dict[str, Any]] = []
    row_warnings: list[dict[str, Any]] = []

    platform = row.get("platform", "").strip()
    text = row.get("text", "").strip()
    image_url = row.get("image_url", "").strip()
    video_url = row.get("video_url", "").strip()
    scheduled_at_str = row.get("scheduled_at", "").strip()

    # Required fields
    if not platform:
        row_errors.append({"row": row_num, "field": "platform", "error": "platform is required"})
    elif platform not in _PUBLISHER_MAP:
        row_errors.append(
            {"row": row_num, "field": "platform", "error": f"unsupported platform: {platform}"}
        )

    if not text and not image_url and not video_url:
        row_errors.append(
            {
                "row": row_num,
                "field": "content",
                "error": "at least one of text, image_url, or video_url is required",
            }
        )

    # Text length
    if text:
        max_chars = PLATFORM_MAX_CHARS.get(platform, 2000)
        if max_chars and len(text) > max_chars:
            row_errors.append(
                {
                    "row": row_num,
                    "field": "text",
                    "error": f"text exceeds {platform} limit of {max_chars} chars ({len(text)} given)",
                }
            )

    # Image URL validation
    if image_url:
        if not image_url.startswith(("http://", "https://")):
            row_errors.append(
                {"row": row_num, "field": "image_url", "error": "image_url must be HTTP(S) URL"}
            )
        if not any(image_url.lower().endswith(ext) for ext in VALID_IMAGE_FORMATS):
            row_warnings.append(
                {
                    "row": row_num,
                    "field": "image_url",
                    "warning": f"image format may be unsupported: {image_url}",
                }
            )

    # Date validation
    if scheduled_at_str:
        try:
            dt = datetime.fromisoformat(scheduled_at_str.replace("Z", "+00:00"))
            if dt < timezone.now() + timedelta(minutes=5):
                row_errors.append(
                    {
                        "row": row_num,
                        "field": "scheduled_at",
                        "error": "scheduled_at must be at least 5 minutes in the future",
                    }
                )
        except ValueError:
            row_errors.append(
                {"row": row_num, "field": "scheduled_at", "error": "invalid datetime format"}
            )
    else:
        row_errors.append(
            {"row": row_num, "field": "scheduled_at", "error": "scheduled_at is required"}
        )

    # Duplicate check
    if text and platform:
        # Check for duplicate content within last 24h
        yesterday = timezone.now() - timedelta(hours=24)
        existing = (
            ScheduledPost.objects.filter(
                platform=platform,
                caption=text,
                scheduled_at__gte=yesterday,
            )
            .exclude(status=ScheduledPost.Status.CANCELLED)
            .first()
        )
        if existing:
            row_warnings.append(
                {
                    "row": row_num,
                    "field": "text",
                    "warning": f"potential duplicate: post {existing.id} has same content",
                }
            )

    return row_errors, row_warnings


def _create_post_from_row(
    row: dict[str, str],
    tenant_id: str,
    user_id: str,
) -> ScheduledPost:
    """Create a ScheduledPost from a validated CSV row."""
    platform = row.get("platform", "").strip()
    account_id = row.get("account_id", "").strip()
    text = row.get("text", "").strip()
    image_url = row.get("image_url", "").strip()
    video_url = row.get("video_url", "").strip()
    scheduled_at_str = row.get("scheduled_at", "").strip()
    tz_str = row.get("timezone", "UTC").strip()
    hashtags_str = row.get("hashtags", "").strip()
    link = row.get("link", "").strip()
    approval_required = row.get("approval_required", "").strip().lower() == "true"

    media_urls: list[str] = []
    if image_url:
        media_urls.append(image_url)
    if video_url:
        media_urls.append(video_url)

    hashtags: list[str] = [h.strip() for h in hashtags_str.split(",") if h.strip()]

    dt = datetime.fromisoformat(scheduled_at_str.replace("Z", "+00:00"))

    post = ScheduledPost.objects.create(
        tenant_id=tenant_id,
        platform=platform,
        account_id=account_id or "00000000-0000-0000-0000-000000000000",
        caption=text,
        hashtags=hashtags,
        media_urls=media_urls,
        link=link,
        scheduled_at=dt,
        timezone=tz_str,
        status=ScheduledPost.Status.SCHEDULED,
        priority=ScheduledPost.Priority.LOW,
        created_by=user_id,
    )

    # Create calendar entry
    ContentCalendar.objects.create(
        tenant_id=tenant_id,
        scheduled_post=post,
        calendar_view=ContentCalendar.CalendarView.MONTH,
    )

    # Queue
    PublishQueue.objects.get_or_create(
        scheduled_post=post,
        defaults={"queue_priority": 3},
    )

    return post
