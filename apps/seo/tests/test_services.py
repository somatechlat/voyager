"""Tests for SEO services — keyword research, on-page audit, rank tracking."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.seo.models import (
    Keyword,
    KeywordCluster,
    OnPageAudit,
    RankHistory,
    SERPTracking,
)
from apps.seo.services import keywords as kw_service
from apps.seo.services import onpage as onpage_service
from apps.seo.services import rank_tracking as rank_service


@pytest.fixture
def tenant_id() -> str:
    return "test-tenant-seo"


@pytest.fixture
def create_keyword(tenant_id, db):
    def _create(**kwargs):
        defaults = {
            "tenant_id": tenant_id,
            "keyword": f"test keyword {uuid.uuid4().hex[:8]}",
            "location": "US",
            "language": "en",
            "monthly_volume": 1000,
            "difficulty": Decimal("45.50"),
            "cpc": Decimal("2.50"),
            "trend_direction": "stable",
            "trend_growth": Decimal("0.05"),
            "current_position": 5,
            "previous_position": 8,
            "position_change": 3,
            "opportunity_score": Decimal("75.0000"),
            "is_tracked": True,
            "commercial_intent": "informational",
        }
        defaults.update(kwargs)
        return Keyword.objects.create(**defaults)

    return _create


@pytest.fixture
def create_cluster(tenant_id, db):
    def _create(**kwargs):
        defaults = {
            "tenant_id": tenant_id,
            "label": f"Cluster {uuid.uuid4().hex[:8]}",
            "total_volume": 50000,
            "avg_difficulty": Decimal("40.00"),
            "priority_score": Decimal("30000.0000"),
        }
        defaults.update(kwargs)
        return KeywordCluster.objects.create(**defaults)

    return _create


@pytest.fixture
def create_audit(tenant_id, db):
    def _create(**kwargs):
        defaults = {
            "tenant_id": tenant_id,
            "url": f"https://example.com/{uuid.uuid4().hex[:8]}",
            "title": "Test Page",
            "score": Decimal("78.50"),
            "grade": OnPageAudit.Grade.B,
            "word_count": 1200,
            "internal_links": 15,
            "external_links": 5,
            "images_total": 10,
            "images_with_alt": 8,
        }
        defaults.update(kwargs)
        return OnPageAudit.objects.create(**defaults)

    return _create


@pytest.fixture
def create_serp_tracking(tenant_id, db):
    def _create(keyword=None, **kwargs):
        defaults = {
            "tenant_id": tenant_id,
            "keyword": keyword,
            "device": "both",
            "alert_threshold": "medium",
            "is_active": True,
            "current_position": 10,
            "previous_position": 12,
            "position_change": 2,
        }
        defaults.update(kwargs)
        return SERPTracking.objects.create(**defaults)

    return _create


@pytest.fixture
def create_rank_history(db):
    def _create(tracking=None, **kwargs):
        defaults = {
            "tracking": tracking,
            "keyword_text": "test keyword",
            "position": 10,
            "previous_position": 12,
            "position_change": 2,
            "location": "US",
            "device": "desktop",
        }
        defaults.update(kwargs)
        return RankHistory.objects.create(**defaults)

    return _create


# ── Keyword Service Tests ─────────────────────────────────────────


class TestKeywordService:
    def test_list_keywords_returns_results(self, create_keyword):
        k1 = create_keyword(keyword="seo tools")
        k2 = create_keyword(keyword="marketing agency")
        result = kw_service.list_keywords("test-tenant-seo")
        assert result["total"] >= 2
        ids = {k.id for k in result["results"]}
        assert k1.id in ids
        assert k2.id in ids

    def test_list_keywords_platform_filter(self, create_keyword):
        create_keyword(keyword="keyword1")
        result = kw_service.list_keywords("test-tenant-seo", search="keyword1")
        assert result["total"] == 1

    def test_get_keyword_detail(self, create_keyword):
        k = create_keyword(keyword="detailed keyword")
        detail = kw_service.get_keyword_detail(k.id)
        assert detail is not None
        assert detail["keyword"] == "detailed keyword"

    def test_get_keyword_detail_not_found(self):
        detail = kw_service.get_keyword_detail(uuid.uuid4())
        assert detail is None

    def test_create_keyword_from_research(self, tenant_id, db):
        result = kw_service.create_keyword_from_research(
            tenant_id=tenant_id,
            keyword="new research keyword",
            volume=5000,
            difficulty=30.0,
            cpc=1.50,
            location="US",
        )
        assert result["created"] is True
        assert result["keyword"] == "new research keyword"
        assert Keyword.objects.filter(keyword="new research keyword").exists()

    def test_create_keyword_from_research_duplicate(self, tenant_id, create_keyword):
        create_keyword(keyword="dup test", location="US", language="en")
        result = kw_service.create_keyword_from_research(
            tenant_id=tenant_id,
            keyword="dup test",
            volume=100,
            difficulty=10.0,
            location="US",
        )
        assert result["created"] is False

    def test_track_keyword_sets_tracked(self, create_keyword):
        k = create_keyword(is_tracked=False, tracked_at=None)
        updated = kw_service.track_keyword(k.id)
        assert updated.is_tracked is True
        assert updated.tracked_at is not None

    def test_untrack_keyword_clears_tracked(self, create_keyword):
        k = create_keyword(is_tracked=True, tracked_at=timezone.now())
        updated = kw_service.untrack_keyword(k.id)
        assert updated.is_tracked is False
        assert updated.tracked_at is None

    def test_get_keyword_opportunities(self, create_keyword, create_cluster):
        cluster = create_cluster()
        create_keyword(keyword="opp keyword", cluster=cluster, opportunity_score=Decimal("85.00"))
        result = kw_service.get_keyword_opportunities("test-tenant-seo")
        assert result["total"] >= 1

    def test_list_keywords_empty_tenant(self, tenant_id):
        result = kw_service.list_keywords(tenant_id + "-none")
        assert result["total"] == 0
        assert result["results"] == []


# ── On-Page Audit Service Tests ───────────────────────────────────


class TestOnPageService:
    def test_create_audit_for_url(self, tenant_id, db):
        audit = onpage_service.create_audit_for_url(
            tenant_id=tenant_id,
            url="https://example.com/test-page",
            target_keywords=["seo", "audit"],
        )
        assert audit is not None
        assert audit.url == "https://example.com/test-page"
        assert audit.tenant_id == tenant_id
        assert OnPageAudit.objects.filter(id=audit.id).exists()

    def test_get_audit_detail(self, create_audit):
        audit = create_audit(url="https://example.com/page1", title="Page One")
        detail = onpage_service.get_audit_detail(audit.id)
        assert detail is not None
        assert detail["url"] == "https://example.com/page1"
        assert detail["title"] == "Page One"

    def test_get_audit_detail_not_found(self):
        detail = onpage_service.get_audit_detail(uuid.uuid4())
        assert detail is None

    def test_list_audits_by_tenant(self, create_audit):
        create_audit(url="https://a.com/1")
        create_audit(url="https://a.com/2")
        result = onpage_service.list_audits("test-tenant-seo")
        assert result["total"] >= 2

    def test_re_run_audit(self, create_audit, tenant_id):
        old_audit = create_audit(url="https://example.com/old")
        new_audit = onpage_service.re_run_audit(old_audit.id, tenant_id=tenant_id)
        assert new_audit is not None
        assert new_audit.url == old_audit.url

    def test_get_audit_summary(self, create_audit):
        create_audit(score=Decimal("95.00"), grade=OnPageAudit.Grade.A)
        create_audit(score=Decimal("50.00"), grade=OnPageAudit.Grade.D)
        summary = onpage_service.get_audit_summary("test-tenant-seo")
        assert summary["total"] >= 2
        assert summary["avg_score"] is not None
        assert summary["grade_distribution"] is not None

    def test_list_audits_score_filter(self, create_audit):
        create_audit(url="https://high.com", score=Decimal("95.00"))
        create_audit(url="https://low.com", score=Decimal("40.00"))
        result = onpage_service.list_audits("test-tenant-seo", min_score=80.0)
        assert all(float(a.score) >= 80.0 for a in result["results"])


# ── Rank Tracking Service Tests ───────────────────────────────────


class TestRankTrackingService:
    def test_add_tracking(self, create_keyword, tenant_id, db):
        k = create_keyword(keyword="track me")
        tracking = rank_service.add_tracking(
            keyword_id=k.id,
            tenant_id=tenant_id,
            target_url="https://example.com/landing",
        )
        assert tracking is not None
        assert tracking.keyword_id == k.id
        assert tracking.tenant_id == tenant_id
        assert SERPTracking.objects.filter(id=tracking.id).exists()

    def test_get_tracking_detail(self, create_keyword, create_serp_tracking, tenant_id):
        k = create_keyword()
        t = create_serp_tracking(keyword=k, current_position=5)
        detail = rank_service.get_tracking_detail(t.id, tenant_id=tenant_id)
        assert detail is not None
        assert detail["current_position"] == 5

    def test_get_tracking_detail_not_found(self, tenant_id):
        detail = rank_service.get_tracking_detail(99999, tenant_id=tenant_id)
        assert detail is None

    def test_list_tracking(self, create_keyword, create_serp_tracking, tenant_id):
        k1 = create_keyword(keyword="kw1")
        k2 = create_keyword(keyword="kw2")
        create_serp_tracking(keyword=k1)
        create_serp_tracking(keyword=k2)
        result = rank_service.list_tracking(tenant_id=tenant_id)
        assert result["total"] >= 2

    def test_record_rank_check(self, create_keyword, create_serp_tracking, tenant_id):
        k = create_keyword(keyword="rank check kw")
        t = create_serp_tracking(keyword=k, current_position=10, check_count=5)
        entry = rank_service.record_rank_check(
            tracking_id=t.id,
            position=8,
            url="https://example.com/page",
            tenant_id=tenant_id,
        )
        assert entry is not None
        assert entry.position == 8
        assert RankHistory.objects.filter(id=entry.id).exists()

    def test_record_rank_check_creates_history(
        self, create_keyword, create_serp_tracking, tenant_id
    ):
        k = create_keyword(keyword="hist kw")
        t = create_serp_tracking(keyword=k)
        entry = rank_service.record_rank_check(
            tracking_id=t.id,
            position=3,
            url="https://example.com/",
            tenant_id=tenant_id,
        )
        assert entry is not None
        assert entry.position == 3

    def test_get_rank_history(
        self, create_keyword, create_serp_tracking, create_rank_history, tenant_id
    ):
        k = create_keyword()
        t = create_serp_tracking(keyword=k)
        create_rank_history(tracking=t, keyword_text="hist kw", position=5)
        create_rank_history(tracking=t, keyword_text="hist kw", position=3)
        result = rank_service.get_rank_history(tracking_id=t.id, tenant_id=tenant_id)
        assert result["total"] >= 2

    def test_get_rank_history_not_found(self, tenant_id):
        result = rank_service.get_rank_history(tracking_id=99999, tenant_id=tenant_id)
        assert result["total"] == 0
        assert result["results"] == []

    def test_add_tracking_sets_active(self, tenant_id, create_keyword):
        k = create_keyword()
        tracking = rank_service.add_tracking(keyword_id=k.id, tenant_id=tenant_id)
        assert tracking.is_active is True
