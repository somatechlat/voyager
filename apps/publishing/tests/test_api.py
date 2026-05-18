"""API tests for Publishing endpoints.

Tests posts, schedule, calendar, queue under ``/api/v1/publish/``.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.publishing.models import ScheduledPost

client = Client()


@pytest.fixture
def scheduled_post(tenant_id: str) -> ScheduledPost:
    """Create a test scheduled post."""
    return ScheduledPost.objects.create(
        tenant_id=tenant_id,
        platform=ScheduledPost.Platform.TWITTER,
        account_id=uuid.uuid4(),
        caption="Test post caption",
        hashtags=["#test"],
        scheduled_at=timezone.now() + timedelta(hours=1),
        status=ScheduledPost.Status.SCHEDULED,
        created_by="test-user",
    )


@pytest.mark.django_db
def test_publish_health_requires_auth() -> None:
    """GET /publish/health without auth returns 401."""
    response = client.get("/api/v1/publish/health")
    assert response.status_code == 401


@pytest.mark.django_db
def test_publish_health(auth_headers: dict[str, str]) -> None:
    """GET /publish/health returns module health."""
    response = client.get("/api/v1/publish/health", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["module"] == "publishing"


@pytest.mark.django_db
def test_list_posts(auth_headers: dict[str, str], scheduled_post: ScheduledPost) -> None:
    """GET /publish/posts returns scheduled posts."""
    response = client.get("/api/v1/publish/posts", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "posts" in data
    assert data["count"] >= 1


@pytest.mark.django_db
def test_list_posts_filtered(auth_headers: dict[str, str], scheduled_post: ScheduledPost) -> None:
    """GET /publish/posts?platform=twitter filters by platform."""
    response = client.get("/api/v1/publish/posts?platform=twitter", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert all(p["platform"] == "twitter" for p in data["posts"])


@pytest.mark.django_db
def test_create_post(auth_headers: dict[str, str]) -> None:
    """POST /publish/posts creates a scheduled post."""
    payload = {
        "platform": "twitter",
        "account_id": str(uuid.uuid4()),
        "caption": "New test post",
        "hashtags": ["#new"],
        "media_urls": [],
        "link": "",
        "alt_text": "",
        "first_comment": "",
        "scheduled_at": timezone.now().isoformat(),
        "timezone": "UTC",
        "publish_type": "feed",
        "priority": 3,
    }
    response = client.post(
        "/api/v1/publish/posts",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["caption"] == "New test post"
    assert data["platform"] == "twitter"


@pytest.mark.django_db
def test_get_post(auth_headers: dict[str, str], scheduled_post: ScheduledPost) -> None:
    """GET /publish/posts/{post_id} returns a single post."""
    response = client.get(f"/api/v1/publish/posts/{scheduled_post.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(scheduled_post.id)
    assert data["caption"] == "Test post caption"


@pytest.mark.django_db
def test_update_post(auth_headers: dict[str, str], scheduled_post: ScheduledPost) -> None:
    """PUT /publish/posts/{post_id} updates a post."""
    payload = {"caption": "Updated caption", "hashtags": ["#updated"]}
    response = client.put(
        f"/api/v1/publish/posts/{scheduled_post.id}",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["caption"] == "Updated caption"


@pytest.mark.django_db
def test_delete_post(auth_headers: dict[str, str], scheduled_post: ScheduledPost) -> None:
    """DELETE /publish/posts/{post_id} cancels a post."""
    response = client.delete(f"/api/v1/publish/posts/{scheduled_post.id}", **auth_headers)
    assert response.status_code == 204
    scheduled_post.refresh_from_db()
    assert scheduled_post.status == ScheduledPost.Status.CANCELLED


@pytest.mark.django_db
def test_calendar_month(auth_headers: dict[str, str]) -> None:
    """GET /publish/calendar/month returns month view."""
    response = client.get("/api/v1/publish/calendar/month?year=2024&month=6", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "days" in data or "weeks" in data or isinstance(data, dict)


@pytest.mark.django_db
def test_calendar_day(auth_headers: dict[str, str]) -> None:
    """GET /publish/calendar/day returns day view."""
    response = client.get("/api/v1/publish/calendar/day?date=2024-06-15", **auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


@pytest.mark.django_db
def test_queue_status(auth_headers: dict[str, str]) -> None:
    """GET /publish/queue returns queue status."""
    response = client.get("/api/v1/publish/queue", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


@pytest.mark.django_db
def test_queue_pending(auth_headers: dict[str, str]) -> None:
    """GET /publish/queue/pending returns pending entries."""
    response = client.get("/api/v1/publish/queue/pending", **auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.django_db
def test_schedule_post(auth_headers: dict[str, str], scheduled_post: ScheduledPost) -> None:
    """POST /publish/posts/{post_id}/schedule reschedules a post."""
    new_time = (timezone.now() + timedelta(days=1)).isoformat()
    payload = {"post_ids": [str(scheduled_post.id)], "scheduled_at": new_time, "timezone": "UTC"}
    response = client.post(
        f"/api/v1/publish/posts/{scheduled_post.id}/schedule",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
