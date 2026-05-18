"""API tests for Social Media endpoints.

Tests inbox, comments, influencers under ``/api/v1/social/``.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.social_media.models.inbox import InboxMessage
from apps.social_media.models.comments import SocialComment
from apps.social_media.models.influencers import InfluencerProfile

client = Client()


@pytest.fixture
def inbox_message(tenant_id: str) -> InboxMessage:
    """Create a test inbox message."""
    return InboxMessage.objects.create(
        tenant_id=tenant_id,
        platform="twitter",
        account_id="acc-001",
        external_id="msg-001",
        sender_handle="@testuser",
        content="Hello! I have a question.",
        message_type="mention",
        status="unread",
    )


@pytest.fixture
def social_comment(tenant_id: str) -> SocialComment:
    """Create a test social comment."""
    return SocialComment.objects.create(
        tenant_id=tenant_id,
        platform="instagram",
        post_id="post-001",
        external_id="cmt-001",
        author_handle="@commenter",
        content="Great post!",
        sentiment="positive",
        status="new",
    )


@pytest.fixture
def influencer(tenant_id: str) -> InfluencerProfile:
    """Create a test influencer profile."""
    return InfluencerProfile.objects.create(
        tenant_id=tenant_id,
        handle="@influencer",
        platform="instagram",
        display_name="Test Influencer",
        follower_count=50000,
        niche="tech",
        status="active",
    )


@pytest.mark.django_db
def test_social_health_requires_auth() -> None:
    """GET /social/health without auth returns 401."""
    response = client.get("/api/v1/social/health")
    assert response.status_code == 401


@pytest.mark.django_db
def test_social_health(auth_headers: dict[str, str]) -> None:
    """GET /social/health returns module health."""
    response = client.get("/api/v1/social/health", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["module"] == "social_media"


@pytest.mark.django_db
def test_list_inbox(auth_headers: dict[str, str], inbox_message: InboxMessage) -> None:
    """GET /social/inbox returns inbox messages."""
    response = client.get("/api/v1/social/inbox", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_list_comments(auth_headers: dict[str, str], social_comment: SocialComment) -> None:
    """GET /social/comments returns comments."""
    response = client.get("/api/v1/social/comments", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_list_influencers(auth_headers: dict[str, str], influencer: InfluencerProfile) -> None:
    """GET /social/influencers returns influencers."""
    response = client.get("/api/v1/social/influencers", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_influencer(auth_headers: dict[str, str]) -> None:
    """POST /social/influencers creates an influencer profile."""
    payload = {
        "handle": "@newinfluencer",
        "platform": "tiktok",
        "display_name": "New Influencer",
        "follower_count": 100000,
        "niche": "fashion",
        "status": "prospect",
    }
    response = client.post(
        "/api/v1/social/influencers",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["handle"] == "@newinfluencer"
