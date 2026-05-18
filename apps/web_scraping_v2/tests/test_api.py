"""API tests for Web Scraping v2 endpoints.

Tests jobs, monitors, sentiment under ``/api/v1/scraping/``.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.web_scraping_v2.models.scrape import ScrapeJob
from apps.web_scraping_v2.models.competitor import CompetitorMonitor
from apps.web_scraping_v2.models.sentiment import SentimentScore
from apps.web_scraping_v2.models.ocr import OCRJob

client = Client()


@pytest.fixture
def scrape_job(tenant_id: str) -> ScrapeJob:
    """Create a test scrape job."""
    return ScrapeJob.objects.create(
        tenant_id=tenant_id,
        url="https://example.com",
        status="pending",
        scrape_type="full_page",
    )


@pytest.fixture
def competitor_monitor(tenant_id: str) -> CompetitorMonitor:
    """Create a test competitor monitor."""
    return CompetitorMonitor.objects.create(
        tenant_id=tenant_id,
        name="Test Monitor",
        target_url="https://competitor.com",
        check_frequency="daily",
    )


@pytest.mark.django_db
def test_scraping_health_requires_auth() -> None:
    """GET /scraping/health without auth returns 401."""
    response = client.get("/api/v1/scraping/health")
    assert response.status_code == 401


@pytest.mark.django_db
def test_scraping_health(auth_headers: dict[str, str]) -> None:
    """GET /scraping/health returns module health."""
    response = client.get("/api/v1/scraping/health", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.django_db
def test_list_scrape_jobs(auth_headers: dict[str, str], scrape_job: ScrapeJob) -> None:
    """GET /scraping/scrape-jobs returns scrape jobs."""
    response = client.get("/api/v1/scraping/scrape-jobs", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


@pytest.mark.django_db
def test_create_scrape_job(auth_headers: dict[str, str]) -> None:
    """POST /scraping/scrape-jobs creates a job."""
    payload = {"url": "https://test.example.com", "scrape_type": "full_page", "config": {}}
    response = client.post(
        "/api/v1/scraping/scrape-jobs",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://test.example.com"


@pytest.mark.django_db
def test_get_scrape_job(auth_headers: dict[str, str], scrape_job: ScrapeJob) -> None:
    """GET /scraping/scrape-jobs/{job_id} returns a job."""
    response = client.get(f"/api/v1/scraping/scrape-jobs/{scrape_job.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://example.com"


@pytest.mark.django_db
def test_list_competitors(
    auth_headers: dict[str, str], competitor_monitor: CompetitorMonitor
) -> None:
    """GET /scraping/competitors returns competitor monitors."""
    response = client.get("/api/v1/scraping/competitors", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


@pytest.mark.django_db
def test_create_competitor_monitor(auth_headers: dict[str, str]) -> None:
    """POST /scraping/competitors creates a monitor."""
    payload = {
        "name": "API Monitor",
        "target_url": "https://api.example.com",
        "check_frequency": "hourly",
    }
    response = client.post(
        "/api/v1/scraping/competitors",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "API Monitor"


@pytest.mark.django_db
def test_analyze_sentiment(auth_headers: dict[str, str]) -> None:
    """POST /scraping/sentiment/analyze returns sentiment analysis."""
    payload = {"text": "This product is amazing! I love it.", "language": "en"}
    response = client.post(
        "/api/v1/scraping/sentiment/analyze",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "sentiment" in data or "score" in data


@pytest.mark.django_db
def test_list_sentiment_scores(auth_headers: dict[str, str]) -> None:
    """GET /scraping/sentiment/scores returns sentiment scores."""
    response = client.get("/api/v1/scraping/sentiment/scores", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
