"""Tests for PublishQueue, ContentCalendar, BlackoutWindow models."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.publishing.models import BlackoutWindow, ContentCalendar, PublishQueue, ScheduledPost


@pytest.fixture
def tenant_id() -> str:
    """Return a consistent tenant ID for tests."""
    return "test-tenant-001"


@pytest.fixture
def account_id() -> uuid.UUID:
    """Return a consistent account UUID for tests."""
    return uuid.uuid4()


@pytest.fixture
def scheduled_post(tenant_id: str, account_id: uuid.UUID) -> ScheduledPost:
    """Create and return a basic ScheduledPost instance."""
    return ScheduledPost.objects.create(
        tenant_id=tenant_id,
        platform=ScheduledPost.Platform.TWITTER,
        account_id=account_id,
        caption="Hello world! #testing",
        hashtags=["#testing", "#pytest"],
        scheduled_at=timezone.now() + timedelta(hours=1),
        status=ScheduledPost.Status.SCHEDULED,
        created_by="user-001",
    )


@pytest.fixture
def publish_queue(scheduled_post: ScheduledPost) -> PublishQueue:
    """Create and return a PublishQueue entry for a scheduled post."""
    return PublishQueue.objects.create(
        scheduled_post=scheduled_post,
        queue_priority=PublishQueue.QueuePriority.MEDIUM,
    )


# ---------------------------------------------------------------------------
# PublishQueue tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_publish_queue_creation(publish_queue: PublishQueue) -> None:
    """PublishQueue can be created linked to a ScheduledPost."""
    assert publish_queue.id is not None
    assert publish_queue.scheduled_post is not None
    assert publish_queue.queue_priority == 2  # MEDIUM
    assert publish_queue.retry_count == 0
    assert publish_queue.processed_at is None


@pytest.mark.django_db
def test_publish_queue_str(publish_queue: PublishQueue) -> None:
    """String representation includes scheduled post ID and priority."""
    rep = str(publish_queue)
    assert "Queue" in rep
    assert "pri=2" in rep


@pytest.mark.django_db
def test_publish_queue_log_error(publish_queue: PublishQueue) -> None:
    """log_error appends an error entry to the error_log JSON field."""
    publish_queue.log_error("Connection refused")
    assert len(publish_queue.error_log) == 1
    assert publish_queue.error_log[0]["error"] == "Connection refused"
    assert "timestamp" in publish_queue.error_log[0]


@pytest.mark.django_db
def test_publish_queue_log_error_trims_to_50(
    publish_queue: PublishQueue,
) -> None:
    """log_error keeps only the last 50 entries."""
    for i in range(55):
        publish_queue.log_error(f"Error {i}")
    publish_queue.refresh_from_db()
    assert len(publish_queue.error_log) == 50
    assert publish_queue.error_log[-1]["error"] == "Error 54"


@pytest.mark.django_db
def test_publish_queue_mark_processed(publish_queue: PublishQueue) -> None:
    """mark_processed sets processed_at and clears next_retry_at."""
    publish_queue.next_retry_at = timezone.now() + timedelta(minutes=5)
    publish_queue.save()
    publish_queue.mark_processed()
    assert publish_queue.processed_at is not None
    assert publish_queue.next_retry_at is None


@pytest.mark.django_db
def test_publish_queue_schedule_retry(publish_queue: PublishQueue) -> None:
    """schedule_retry increments retry_count and sets next_retry_at."""
    retry_time = timezone.now() + timedelta(minutes=10)
    publish_queue.schedule_retry(retry_time)
    assert publish_queue.retry_count == 1
    assert publish_queue.next_retry_at == retry_time


@pytest.mark.django_db
def test_publish_queue_mark_overflowed(publish_queue: PublishQueue) -> None:
    """mark_overflowed sets overflow_reason and overflowed_at."""
    publish_queue.mark_overflowed("frequency_limit")
    assert publish_queue.overflow_reason == "frequency_limit"
    assert publish_queue.overflowed_at is not None


@pytest.mark.django_db
def test_publish_queue_get_pending(
    scheduled_post: ScheduledPost,
    publish_queue: PublishQueue,
) -> None:
    """get_pending returns unprocessed queue entries."""
    pending = PublishQueue.get_pending()
    assert pending.count() == 1


@pytest.mark.django_db
def test_publish_queue_get_pending_excludes_processed(
    publish_queue: PublishQueue,
) -> None:
    """get_pending excludes already processed entries."""
    publish_queue.mark_processed()
    pending = PublishQueue.get_pending()
    assert pending.count() == 0


# ---------------------------------------------------------------------------
# ContentCalendar tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_content_calendar_creation(
    scheduled_post: ScheduledPost,
    tenant_id: str,
) -> None:
    """ContentCalendar can be created linked to a ScheduledPost."""
    cal = ContentCalendar.objects.create(
        tenant_id=tenant_id,
        scheduled_post=scheduled_post,
        calendar_view=ContentCalendar.CalendarView.MONTH,
        position_order=1,
        color_override="#FF5733",
    )
    assert cal.id is not None
    assert isinstance(cal.id, uuid.UUID)
    assert cal.scheduled_post == scheduled_post
    assert cal.calendar_view == "month"
    assert cal.position_order == 1
    assert cal.color_override == "#FF5733"


@pytest.mark.django_db
def test_content_calendar_str(
    scheduled_post: ScheduledPost,
    tenant_id: str,
) -> None:
    """String representation includes calendar view."""
    cal = ContentCalendar.objects.create(
        tenant_id=tenant_id,
        scheduled_post=scheduled_post,
        calendar_view=ContentCalendar.CalendarView.WEEK,
    )
    assert "week" in str(cal)


@pytest.mark.django_db
def test_content_calendar_default_view(
    scheduled_post: ScheduledPost,
    tenant_id: str,
) -> None:
    """ContentCalendar defaults to MONTH view."""
    cal = ContentCalendar.objects.create(
        tenant_id=tenant_id,
        scheduled_post=scheduled_post,
    )
    assert cal.calendar_view == ContentCalendar.CalendarView.MONTH
    assert cal.position_order == 0


# ---------------------------------------------------------------------------
# BlackoutWindow tests
# ---------------------------------------------------------------------------


@pytest.fixture
def blackout_window(tenant_id: str) -> BlackoutWindow:
    """Create and return a BlackoutWindow instance."""
    return BlackoutWindow.objects.create(
        tenant_id=tenant_id,
        name="Holiday Blackout",
        start_at=timezone.now() + timedelta(days=1),
        end_at=timezone.now() + timedelta(days=2),
        recurring=BlackoutWindow.RecurringType.NONE,
        is_active=True,
    )


@pytest.mark.django_db
def test_blackout_window_creation(blackout_window: BlackoutWindow) -> None:
    """BlackoutWindow can be created with all required fields."""
    assert blackout_window.id is not None
    assert isinstance(blackout_window.id, uuid.UUID)
    assert blackout_window.name == "Holiday Blackout"
    assert blackout_window.recurring == "none"
    assert blackout_window.is_active is True


@pytest.mark.django_db
def test_blackout_window_str(blackout_window: BlackoutWindow) -> None:
    """String representation includes name and time range."""
    assert "Holiday Blackout" in str(blackout_window)


@pytest.mark.django_db
def test_blackout_window_is_blackout_active(
    blackout_window: BlackoutWindow,
) -> None:
    """is_blackout returns True for datetime within the window."""
    check_time = blackout_window.start_at + timedelta(hours=1)
    assert blackout_window.is_blackout(check_time) is True


@pytest.mark.django_db
def test_blackout_window_is_blackout_inactive(
    blackout_window: BlackoutWindow,
) -> None:
    """is_blackout returns False when window is not active."""
    blackout_window.is_active = False
    blackout_window.save()
    check_time = blackout_window.start_at + timedelta(hours=1)
    assert blackout_window.is_blackout(check_time) is False


@pytest.mark.django_db
def test_blackout_window_is_blackout_outside_range(
    blackout_window: BlackoutWindow,
) -> None:
    """is_blackout returns False for datetime outside the window."""
    check_time = blackout_window.end_at + timedelta(hours=1)
    assert blackout_window.is_blackout(check_time) is False


@pytest.mark.django_db
def test_blackout_window_daily_recurring(tenant_id: str) -> None:
    """Daily recurring blackout checks time component only."""
    base = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    bw = BlackoutWindow.objects.create(
        tenant_id=tenant_id,
        name="Daily Lunch Break",
        start_at=base,
        end_at=base.replace(hour=10),
        recurring=BlackoutWindow.RecurringType.DAILY,
        is_active=True,
    )
    check_in = base.replace(hour=9, minute=30)
    check_out = base.replace(hour=11, minute=0)
    assert bw.is_blackout(check_in) is True
    assert bw.is_blackout(check_out) is False


@pytest.mark.django_db
def test_blackout_window_account_scope(
    tenant_id: str,
    account_id: uuid.UUID,
) -> None:
    """BlackoutWindow can be scoped to a specific account."""
    bw = BlackoutWindow.objects.create(
        tenant_id=tenant_id,
        name="Account Blackout",
        start_at=timezone.now(),
        end_at=timezone.now() + timedelta(hours=2),
        account_id=account_id,
        platform="twitter",
    )
    assert bw.account_id == account_id
    assert bw.platform == "twitter"
