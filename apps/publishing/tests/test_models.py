"""Tests for Publishing models: ScheduledPost."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.publishing.models import ScheduledPost

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# ScheduledPost tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_scheduled_post_creation(scheduled_post: ScheduledPost) -> None:
    """ScheduledPost can be created with all required fields."""
    assert scheduled_post.id is not None
    assert isinstance(scheduled_post.id, uuid.UUID)
    assert scheduled_post.platform == "twitter"
    assert scheduled_post.caption == "Hello world! #testing"
    assert scheduled_post.hashtags == ["#testing", "#pytest"]
    assert scheduled_post.status == "scheduled"
    assert scheduled_post.created_by == "user-001"


@pytest.mark.django_db
def test_scheduled_post_str(scheduled_post: ScheduledPost) -> None:
    """String representation includes platform, caption and status."""
    rep = str(scheduled_post)
    assert "twitter" in rep
    assert "Hello world!" in rep
    assert "scheduled" in rep


@pytest.mark.django_db
def test_scheduled_post_default_status(tenant_id: str, account_id: uuid.UUID) -> None:
    """ScheduledPost defaults to DRAFT status."""
    post = ScheduledPost.objects.create(
        tenant_id=tenant_id,
        platform=ScheduledPost.Platform.INSTAGRAM,
        account_id=account_id,
        scheduled_at=timezone.now() + timedelta(hours=1),
        created_by="user-001",
    )
    assert post.status == ScheduledPost.Status.DRAFT
    assert post.publish_type == ScheduledPost.PublishType.FEED
    assert post.priority == ScheduledPost.Priority.LOW


@pytest.mark.django_db
def test_scheduled_post_all_platforms(tenant_id: str, account_id: uuid.UUID) -> None:
    """All Platform choices can be stored."""
    for idx, (value, _label) in enumerate(ScheduledPost.Platform.choices):
        post = ScheduledPost.objects.create(
            tenant_id=tenant_id,
            platform=value,
            account_id=uuid.uuid4(),
            scheduled_at=timezone.now() + timedelta(minutes=idx + 1),
            created_by="user-001",
        )
        assert post.platform == value


@pytest.mark.django_db
def test_scheduled_post_all_statuses(tenant_id: str, account_id: uuid.UUID) -> None:
    """All Status choices can be stored."""
    for idx, (value, _label) in enumerate(ScheduledPost.Status.choices):
        post = ScheduledPost.objects.create(
            tenant_id=tenant_id,
            platform=ScheduledPost.Platform.LINKEDIN,
            account_id=uuid.uuid4(),
            scheduled_at=timezone.now() + timedelta(minutes=idx + 1),
            status=value,
            created_by="user-001",
        )
        assert post.status == value


@pytest.mark.django_db
def test_scheduled_post_priority_levels(tenant_id: str, account_id: uuid.UUID) -> None:
    """All Priority choices can be stored."""
    for value, _label in ScheduledPost.Priority.choices:
        post = ScheduledPost.objects.create(
            tenant_id=tenant_id,
            platform=ScheduledPost.Platform.FACEBOOK,
            account_id=uuid.uuid4(),
            scheduled_at=timezone.now() + timedelta(hours=1),
            priority=value,
            created_by="user-001",
        )
        assert post.priority == value


@pytest.mark.django_db
def test_scheduled_post_is_due(tenant_id: str, account_id: uuid.UUID) -> None:
    """is_due returns True when status is SCHEDULED and time has passed."""
    post = ScheduledPost.objects.create(
        tenant_id=tenant_id,
        platform=ScheduledPost.Platform.TWITTER,
        account_id=uuid.uuid4(),
        scheduled_at=timezone.now() - timedelta(minutes=5),
        status=ScheduledPost.Status.SCHEDULED,
        created_by="user-001",
    )
    assert post.is_due() is True


@pytest.mark.django_db
def test_scheduled_post_is_due_not_scheduled(
    tenant_id: str,
    account_id: uuid.UUID,
) -> None:
    """is_due returns False when status is not SCHEDULED."""
    post = ScheduledPost.objects.create(
        tenant_id=tenant_id,
        platform=ScheduledPost.Platform.TWITTER,
        account_id=uuid.uuid4(),
        scheduled_at=timezone.now() - timedelta(minutes=5),
        status=ScheduledPost.Status.DRAFT,
        created_by="user-001",
    )
    assert post.is_due() is False


@pytest.mark.django_db
def test_scheduled_post_can_publish_approved(
    tenant_id: str,
    account_id: uuid.UUID,
) -> None:
    """can_publish returns True for approved post without workflow."""
    post = ScheduledPost.objects.create(
        tenant_id=tenant_id,
        platform=ScheduledPost.Platform.TWITTER,
        account_id=uuid.uuid4(),
        scheduled_at=timezone.now() + timedelta(minutes=5),
        status=ScheduledPost.Status.APPROVED,
        approval_status=ScheduledPost.ApprovalStatus.NOT_REQUIRED,
        created_by="user-001",
    )
    assert post.can_publish() is True


@pytest.mark.django_db
def test_scheduled_post_can_publish_rejected(
    tenant_id: str,
    account_id: uuid.UUID,
) -> None:
    """can_publish returns False when approval_status is REJECTED."""
    post = ScheduledPost.objects.create(
        tenant_id=tenant_id,
        platform=ScheduledPost.Platform.TWITTER,
        account_id=uuid.uuid4(),
        scheduled_at=timezone.now() + timedelta(minutes=5),
        status=ScheduledPost.Status.SCHEDULED,
        approval_status=ScheduledPost.ApprovalStatus.REJECTED,
        created_by="user-001",
    )
    assert post.can_publish() is False


@pytest.mark.django_db
def test_scheduled_post_can_publish_workflow_pending(
    tenant_id: str,
    account_id: uuid.UUID,
) -> None:
    """can_publish returns False when approval workflow is pending."""
    post = ScheduledPost.objects.create(
        tenant_id=tenant_id,
        platform=ScheduledPost.Platform.TWITTER,
        account_id=uuid.uuid4(),
        scheduled_at=timezone.now() + timedelta(minutes=5),
        status=ScheduledPost.Status.SCHEDULED,
        approval_workflow_id=uuid.uuid4(),
        approval_status=ScheduledPost.ApprovalStatus.PENDING,
        created_by="user-001",
    )
    assert post.can_publish() is False


@pytest.mark.django_db
def test_scheduled_post_mark_published(
    scheduled_post: ScheduledPost,
) -> None:
    """mark_published updates status, platform_post_id and published_at."""
    scheduled_post.mark_published("twitter-12345")
    assert scheduled_post.status == ScheduledPost.Status.PUBLISHED
    assert scheduled_post.platform_post_id == "twitter-12345"
    assert scheduled_post.published_at is not None
    assert scheduled_post.last_error == ""


@pytest.mark.django_db
def test_scheduled_post_mark_failed(
    scheduled_post: ScheduledPost,
) -> None:
    """mark_failed updates status and error."""
    scheduled_post.mark_failed("API rate limit exceeded")
    assert scheduled_post.status == ScheduledPost.Status.FAILED
    assert scheduled_post.last_error == "API rate limit exceeded"
    assert scheduled_post.last_attempt_at is not None


@pytest.mark.django_db
def test_scheduled_post_record_attempt(
    scheduled_post: ScheduledPost,
) -> None:
    """record_attempt increments publish_attempts and stores error."""
    scheduled_post.record_attempt("Connection timeout")
    assert scheduled_post.publish_attempts == 1
    assert scheduled_post.last_error == "Connection timeout"
    assert scheduled_post.last_attempt_at is not None


@pytest.mark.django_db
def test_scheduled_post_dedup_hash(tenant_id: str, account_id: uuid.UUID) -> None:
    """dedup_hash can be set for duplicate detection."""
    post = ScheduledPost.objects.create(
        tenant_id=tenant_id,
        platform=ScheduledPost.Platform.TWITTER,
        account_id=account_id,
        scheduled_at=timezone.now() + timedelta(hours=1),
        caption="Test",
        created_by="user-001",
        dedup_hash="abc123" * 8,
    )
    assert post.dedup_hash == "abc123" * 8
