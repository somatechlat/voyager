"""API tests for SEO endpoints.

Tests keywords, audits, rank tracking under ``/api/v1/seo/``.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.seo.models.keyword import Keyword
from apps.seo.models.onpage import OnPageAudit
from apps.seo.models.rank import SERPTracking

client = Client()


@pytest.fixture
def keyword() -> Keyword:
    """Create a test keyword."""
    return Keyword.objects.create(
        keyword="marketing automation",
        search_volume=5000,
        difficulty=45,
        cpc=2.50,
        language="en",
    )


@pytest.fixture
def audit() -> OnPageAudit:
    """Create a test on-page audit."""
    return OnPageAudit.objects.create(
        url="https://example.com/page",
        title="Test Page",
        score=78,
        status="completed",
    )


@pytest.fixture
def serp_tracking() -> SERPTracking:
    """Create a test SERP tracking entry."""
    return SERPTracking.objects.create(
        keyword="marketing automation",
        url="https://example.com",
        rank=5,
        search_engine="google",
        location="US",
    )


@pytest.mark.django_db
def test_seo_health_requires_auth() -> None:
    """GET /seo/health without auth returns 401."""
    response = client.get("/api/v1/seo/health")
    assert response.status_code == 401


@pytest.mark.django_db
def test_seo_health(auth_headers: dict[str, str]) -> None:
    """GET /seo/health returns module health."""
    response = client.get("/api/v1/seo/health", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["module"] == "seo"


@pytest.mark.django_db
def test_list_keywords(auth_headers: dict[str, str], keyword: Keyword) -> None:
    """GET /seo/keywords returns keywords."""
    response = client.get("/api/v1/seo/keywords", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_keyword(auth_headers: dict[str, str]) -> None:
    """POST /seo/keywords creates a keyword."""
    payload = {
        "keyword": "ai marketing tools",
        "search_volume": 10000,
        "difficulty": 60,
        "cpc": 4.00,
        "language": "en",
    }
    response = client.post(
        "/api/v1/seo/keywords",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["keyword"] == "ai marketing tools"


@pytest.mark.django_db
def test_get_keyword(auth_headers: dict[str, str], keyword: Keyword) -> None:
    """GET /seo/keywords/{id} returns a keyword."""
    response = client.get(f"/api/v1/seo/keywords/{keyword.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["keyword"] == "marketing automation"


@pytest.mark.django_db
def test_list_audits(auth_headers: dict[str, str], audit: OnPageAudit) -> None:
    """GET /seo/audits/onpage returns audits."""
    response = client.get("/api/v1/seo/audits/onpage", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_list_rank_tracking(auth_headers: dict[str, str], serp_tracking: SERPTracking) -> None:
    """GET /seo/rank-tracking returns SERP tracking data."""
    response = client.get("/api/v1/seo/rank-tracking", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
