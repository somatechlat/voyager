"""Tests for social_media services — inbox, comments, community."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.social_media.models import CommunityMember, InboxMessage, SocialComment
from apps.social_media.services import comments as comment_service
from apps.social_media.services import community as community_service
from apps.social_media.services import inbox as inbox_service


@pytest.fixture
def tenant_id() -> str:
    return "test-tenant-1"


@pytest.fixture
def create_inbox_message(tenant_id, db):
    def _create(**kwargs):
        defaults = {
            "tenant_id": tenant_id,
            "platform": "instagram",
            "platform_message_id": str(uuid.uuid4()),
            "type": "comment",
            "author_name": "Test User",
            "author_platform_id": str(uuid.uuid4()),
            "text": "Test message",
            "status": "new",
            "received_at": timezone.now(),
        }
        defaults.update(kwargs)
        return InboxMessage.objects.create(**defaults)

    return _create


@pytest.fixture
def create_comment(tenant_id, db):
    def _create(**kwargs):
        defaults = {
            "tenant_id": tenant_id,
            "platform": "instagram",
            "platform_comment_id": str(uuid.uuid4()),
            "post_id": str(uuid.uuid4()),
            "author_name": "Test Author",
            "author_platform_id": str(uuid.uuid4()),
            "text": "Test comment",
            "received_at": timezone.now(),
        }
        defaults.update(kwargs)
        return SocialComment.objects.create(**defaults)

    return _create


@pytest.fixture
def create_member(tenant_id, db):
    def _create(**kwargs):
        defaults = {
            "tenant_id": tenant_id,
            "platform": "instagram",
            "platform_user_id": str(uuid.uuid4()),
            "name": "Test Member",
            "followers": 100,
            "following": 50,
            "engagement_score": Decimal("5.50"),
            "influence_score": Decimal("3.00"),
            "loyalty_score": Decimal("4.00"),
            "vip_score": Decimal("45.00"),
            "tier": "engaged",
            "interaction_breakdown": {"comments": 5, "likes": 20},
        }
        defaults.update(kwargs)
        return CommunityMember.objects.create(**defaults)

    return _create


# ── Inbox Service Tests ───────────────────────────────────────────


class TestInboxService:
    def test_fetch_unified_inbox_returns_all_messages(self, create_inbox_message):
        msg1 = create_inbox_message(author_name="Alice", text="Hello")
        msg2 = create_inbox_message(author_name="Bob", text="Hi there")
        result = inbox_service.fetch_unified_inbox("test-tenant-1", limit=10)
        assert result["total"] == 2
        assert len(result["results"]) == 2
        ids = {str(m.id) for m in result["results"]}
        assert str(msg1.id) in ids
        assert str(msg2.id) in ids

    def test_fetch_unified_inbox_platform_filter(self, create_inbox_message):
        create_inbox_message(platform="instagram", text="IG msg")
        create_inbox_message(platform="twitter", text="TW msg")
        result = inbox_service.fetch_unified_inbox("test-tenant-1", platform="twitter")
        assert result["total"] == 1
        assert result["results"][0].text == "TW msg"

    def test_fetch_unified_inbox_status_filter(self, create_inbox_message):
        create_inbox_message(status="new")
        create_inbox_message(status="read")
        result = inbox_service.fetch_unified_inbox("test-tenant-1", status="read")
        assert result["total"] == 1
        assert result["results"][0].status == "read"

    def test_assign_message_updates_assignment(self, create_inbox_message):
        msg = create_inbox_message(assigned_to="")
        updated = inbox_service.assign_message(msg, "user-123", "manual")
        assert updated.assigned_to == "user-123"
        assert updated.assignment_reason == "manual"

    def test_batch_assign_filters_by_query(self, create_inbox_message):
        create_inbox_message(status="new", assigned_to="")
        create_inbox_message(status="new", assigned_to="")
        result = inbox_service.batch_assign("test-tenant-1", "user-456", reason="auto")
        assert result["assigned"] == 2

    def test_get_message_thread(self, create_inbox_message):
        thread_id = uuid.uuid4()
        parent = create_inbox_message(thread_id=None, text="Parent")
        child1 = create_inbox_message(parent=parent, thread_id=thread_id, text="Child1")
        child2 = create_inbox_message(parent=parent, thread_id=thread_id, text="Child2")
        thread = inbox_service.get_message_thread(parent.id)
        assert thread is not None
        assert thread["message"].id == parent.id
        reply_ids = {r.id for r in thread["replies"]}
        assert child1.id in reply_ids
        assert child2.id in reply_ids

    def test_get_message_thread_not_found(self):
        result = inbox_service.get_message_thread(uuid.uuid4())
        assert result is None

    def test_fetch_unified_inbox_empty_result(self, tenant_id):
        result = inbox_service.fetch_unified_inbox(tenant_id + "-none")
        assert result["total"] == 0
        assert result["results"] == []


# ── Comments Service Tests ────────────────────────────────────────


class TestCommentService:
    def test_list_comments_returns_all(self, create_comment):
        c1 = create_comment(text="First")
        c2 = create_comment(text="Second")
        result = comment_service.list_comments("test-tenant-1")
        assert result["total"] >= 2
        ids = {c.id for c in result["results"]}
        assert c1.id in ids
        assert c2.id in ids

    def test_list_comments_post_filter(self, create_comment):
        post_id = str(uuid.uuid4())
        create_comment(post_id=post_id, text="Match")
        create_comment(post_id=str(uuid.uuid4()), text="No match")
        result = comment_service.list_comments("test-tenant-1", post_id=post_id)
        assert result["total"] == 1
        assert result["results"][0].text == "Match"

    def test_hide_comment_sets_hidden(self, create_comment):
        c = create_comment(is_hidden=False)
        updated = comment_service.hide_comment(c, "spam", "admin-1")
        assert updated.is_hidden is True
        assert updated.hidden_reason == "spam"

    def test_unhide_comment_sets_visible(self, create_comment):
        c = create_comment(is_hidden=True, hidden_reason="spam")
        updated = comment_service.unhide_comment(c, "admin-1")
        assert updated.is_hidden is False
        assert updated.hidden_reason == ""

    def test_reply_to_comment(self, create_comment):
        c = create_comment(reply_text="")
        updated = comment_service.reply_to_comment(c, "Thanks!", "admin-2")
        assert updated.reply_text == "Thanks!"
        assert updated.replied_by == "admin-2"
        assert updated.replied_at is not None

    def test_build_reply_suggestions_with_tone(self):
        suggestions = comment_service.build_reply_suggestions("Great product!", tone="friendly")
        assert len(suggestions) == 3
        assert all(suggestions)

    def test_build_reply_suggestions_empty_tone(self):
        suggestions = comment_service.build_reply_suggestions("Thanks")
        assert len(suggestions) == 3


# ── Community Service Tests ───────────────────────────────────────


class TestCommunityService:
    def test_list_community_members(self, create_member):
        m1 = create_member(name="Alice")
        m2 = create_member(name="Bob")
        result = community_service.list_community_members("test-tenant-1")
        assert result["total"] >= 2
        ids = {m.id for m in result["results"]}
        assert m1.id in ids
        assert m2.id in ids

    def test_get_community_member_by_id(self, create_member):
        m = create_member(name="Charlie")
        result = community_service.get_community_member(str(m.id))
        assert result is not None
        assert result.name == "Charlie"

    def test_get_community_member_not_found(self):
        result = community_service.get_community_member(str(uuid.uuid4()))
        assert result is None

    def test_list_community_by_tier(self, create_member):
        create_member(tier="champion", vip_score=Decimal("95.00"))
        create_member(tier="passive", vip_score=Decimal("10.00"))
        result = community_service.list_community_by_tier("test-tenant-1", "champion")
        assert result["total"] == 1
        assert result["results"][0].tier == "champion"

    def test_list_community_by_tier_empty(self, tenant_id):
        result = community_service.list_community_by_tier(tenant_id + "-none", "champion")
        assert result["total"] == 0
        assert result["results"] == []

    def test_calculate_vip_tier(self, create_member):
        m = create_member(engagement_score=Decimal("85.00"), tier="passive")
        result = community_service.calculate_vip_tier(m)
        assert result is not None
        assert result.tier in ("champion", "advocate", "engaged", "passive")

    def test_calculate_vip_tier_zero_scores(self, create_member):
        m = create_member(
            engagement_score=Decimal("0.00"),
            influence_score=Decimal("0.00"),
            loyalty_score=Decimal("0.00"),
        )
        result = community_service.calculate_vip_tier(m)
        assert result is not None

    def test_list_community_members_with_engagement_score(self, create_member):
        create_member(name="High", engagement_score=Decimal("100.00"))
        create_member(name="Low", engagement_score=Decimal("1.00"))
        result = community_service.list_community_members(
            "test-tenant-1", min_engagement_score=50.0
        )
        assert all(float(m.engagement_score) >= 50.0 for m in result["results"])
