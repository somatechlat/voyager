"""Tests for Web Scraping v2 models: ScrapeJob, CompetitorMonitor, SentimentScore."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.web_scraping_v2.models import (
    CompetitorChange,
    CompetitorMonitor,
    CompetitorSnapshot,
    ScrapeJob,
    SentimentScore,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tenant_id() -> str:
    """Return a consistent tenant ID for tests."""
    return "test-tenant-001"


@pytest.fixture
def scrape_job(tenant_id: str) -> ScrapeJob:
    """Create and return a ScrapeJob instance."""
    return ScrapeJob.objects.create(
        tenant_id=tenant_id,
        url="https://example.com/page",
        selector=".content h1",
        proxy_used="proxy-1.example.com",
        status=ScrapeJob.Status.PENDING,
    )


@pytest.fixture
def competitor_monitor(tenant_id: str) -> CompetitorMonitor:
    """Create and return a CompetitorMonitor instance."""
    return CompetitorMonitor.objects.create(
        tenant_id=tenant_id,
        name="Acme Competitor",
        url="https://acme.example.com",
        check_interval_minutes=120,
        is_active=True,
    )


@pytest.fixture
def sentiment_score(tenant_id: str) -> SentimentScore:
    """Create and return a SentimentScore instance."""
    return SentimentScore.objects.create(
        tenant_id=tenant_id,
        text="This product is amazing and works perfectly!",
        text_hash="abc123def456" * 4,
        source_type="review",
        source_id="review-001",
        model=SentimentScore.ModelType.BERT,
        overall_sentiment=SentimentScore.Sentiment.POSITIVE,
        overall_score=Decimal("0.875"),
        confidence=Decimal("0.950"),
        aspects=[
            {"aspect": "quality", "sentiment": "positive", "score": 0.9},
            {"aspect": "usability", "sentiment": "positive", "score": 0.85},
        ],
        emotions={"joy": 0.8, "trust": 0.7, "surprise": 0.2},
        language="en",
    )


from decimal import Decimal  # noqa: E402, pylint: disable=wrong-import-position

# ---------------------------------------------------------------------------
# ScrapeJob tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_scrape_job_creation(scrape_job: ScrapeJob) -> None:
    """ScrapeJob can be created with all required fields."""
    assert scrape_job.id is not None
    assert isinstance(scrape_job.id, uuid.UUID)
    assert scrape_job.tenant_id == "test-tenant-001"
    assert scrape_job.url == "https://example.com/page"
    assert scrape_job.selector == ".content h1"
    assert scrape_job.proxy_used == "proxy-1.example.com"
    assert scrape_job.status == "pending"


@pytest.mark.django_db
def test_scrape_job_str(scrape_job: ScrapeJob) -> None:
    """String representation includes URL and status."""
    rep = str(scrape_job)
    assert "https://example.com/page" in rep
    assert "pending" in rep


@pytest.mark.django_db
def test_scrape_job_defaults(tenant_id: str) -> None:
    """ScrapeJob fields have correct defaults."""
    job = ScrapeJob.objects.create(
        tenant_id=tenant_id,
        url="https://example.com",
    )
    assert job.selector == ""
    assert job.proxy_used == ""
    assert job.status == ScrapeJob.Status.PENDING
    assert job.content_text == ""
    assert job.content_html == ""
    assert job.metadata == {}
    assert job.error_message == ""
    assert job.started_at is None
    assert job.completed_at is None


@pytest.mark.django_db
def test_scrape_job_all_statuses(tenant_id: str) -> None:
    """All Status choices can be stored."""
    for value, _label in ScrapeJob.Status.choices:
        job = ScrapeJob.objects.create(
            tenant_id=tenant_id,
            url=f"https://example.com/{value}",
            status=value,
        )
        assert job.status == value


@pytest.mark.django_db
def test_scrape_job_content_fields(tenant_id: str) -> None:
    """ScrapeJob content fields can store extracted data."""
    job = ScrapeJob.objects.create(
        tenant_id=tenant_id,
        url="https://example.com/article",
        content_text="Article body text here.",
        content_html="<article>Article body text here.</article>",
        metadata={
            "status_code": 200,
            "headers": {"content-type": "text/html"},
            "response_time_ms": 450,
        },
    )
    assert job.content_text == "Article body text here."
    assert job.metadata["status_code"] == 200


@pytest.mark.django_db
def test_scrape_job_error_message(tenant_id: str) -> None:
    """ScrapeJob error_message stores failure description."""
    job = ScrapeJob.objects.create(
        tenant_id=tenant_id,
        url="https://example.com/broken",
        status=ScrapeJob.Status.FAILED,
        error_message="Connection timeout after 30s",
    )
    assert job.error_message == "Connection timeout after 30s"


@pytest.mark.django_db
def test_scrape_job_timestamps(tenant_id: str) -> None:
    """ScrapeJob has created_at and updated_at timestamps."""
    job = ScrapeJob.objects.create(
        tenant_id=tenant_id,
        url="https://example.com",
        started_at=timezone.now(),
        completed_at=timezone.now() + timedelta(seconds=5),
    )
    assert job.created_at is not None
    assert job.updated_at is not None
    assert job.started_at is not None
    assert job.completed_at is not None


# ---------------------------------------------------------------------------
# CompetitorMonitor tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_competitor_monitor_creation(competitor_monitor: CompetitorMonitor) -> None:
    """CompetitorMonitor can be created with all required fields."""
    assert competitor_monitor.id is not None
    assert isinstance(competitor_monitor.id, uuid.UUID)
    assert competitor_monitor.name == "Acme Competitor"
    assert competitor_monitor.tenant_id == "test-tenant-001"
    assert competitor_monitor.url == "https://acme.example.com"
    assert competitor_monitor.check_interval_minutes == 120
    assert competitor_monitor.is_active is True


@pytest.mark.django_db
def test_competitor_monitor_str(competitor_monitor: CompetitorMonitor) -> None:
    """String representation includes name."""
    assert str(competitor_monitor) == "CompetitorMonitor(Acme Competitor)"


@pytest.mark.django_db
def test_competitor_monitor_defaults(tenant_id: str) -> None:
    """CompetitorMonitor fields have correct defaults."""
    cm = CompetitorMonitor.objects.create(
        tenant_id=tenant_id,
        name="New Monitor",
        url="https://example.com",
    )
    assert cm.check_interval_minutes == 60
    assert cm.is_active is True
    assert cm.last_checked_at is None


@pytest.mark.django_db
def test_competitor_monitor_inactive(tenant_id: str) -> None:
    """CompetitorMonitor can be set to inactive."""
    cm = CompetitorMonitor.objects.create(
        tenant_id=tenant_id,
        name="Inactive Monitor",
        url="https://example.com",
        is_active=False,
    )
    assert cm.is_active is False


@pytest.mark.django_db
def test_competitor_monitor_last_checked(tenant_id: str) -> None:
    """last_checked_at stores timestamp of last check."""
    now = timezone.now()
    cm = CompetitorMonitor.objects.create(
        tenant_id=tenant_id,
        name="Checked Monitor",
        url="https://example.com",
        last_checked_at=now,
    )
    assert cm.last_checked_at == now


@pytest.mark.django_db
def test_competitor_monitor_snapshot(
    competitor_monitor: CompetitorMonitor,
) -> None:
    """CompetitorSnapshot stores a scraped page snapshot."""
    snapshot = CompetitorSnapshot.objects.create(
        competitor=competitor_monitor,
        url="https://acme.example.com/pricing",
        content_hash="a" * 64,
        content_text="Pricing: Starter $10, Pro $50",
        dom_structure={"tag": "div", "children": [{"tag": "h1"}]},
        screenshot_path="s3://bucket/screenshots/001.png",
        prices=[{"product": "Starter", "price": 10.0}, {"product": "Pro", "price": 50.0}],
        products=["Starter", "Pro"],
    )
    assert snapshot.id is not None
    assert snapshot.competitor == competitor_monitor
    assert snapshot.content_hash == "a" * 64
    assert snapshot.prices[0]["price"] == 10.0


@pytest.mark.django_db
def test_competitor_snapshot_str(competitor_monitor: CompetitorMonitor) -> None:
    """String representation includes competitor name."""
    snapshot = CompetitorSnapshot.objects.create(
        competitor=competitor_monitor,
        url="https://acme.example.com",
        content_hash="b" * 64,
    )
    rep = str(snapshot)
    assert "Acme Competitor" in rep


@pytest.mark.django_db
def test_competitor_monitor_change(
    competitor_monitor: CompetitorMonitor,
) -> None:
    """CompetitorChange stores detected changes."""
    change = CompetitorChange.objects.create(
        competitor=competitor_monitor,
        url="https://acme.example.com/pricing",
        change_type=CompetitorChange.ChangeType.PRICE_CHANGE,
        change_details={
            "product": "Pro",
            "old_price": 45.0,
            "new_price": 50.0,
            "diff": 5.0,
        },
    )
    assert change.id is not None
    assert change.competitor == competitor_monitor
    assert change.change_type == "price_change"
    assert change.change_details["old_price"] == 45.0


@pytest.mark.django_db
def test_competitor_change_all_types(competitor_monitor: CompetitorMonitor) -> None:
    """All ChangeType choices can be stored."""
    for value, _label in CompetitorChange.ChangeType.choices:
        change = CompetitorChange.objects.create(
            competitor=competitor_monitor,
            url=f"https://example.com/{value}",
            change_type=value,
        )
        assert change.change_type == value


@pytest.mark.django_db
def test_competitor_change_str(competitor_monitor: CompetitorMonitor) -> None:
    """String representation includes competitor name and change type."""
    change = CompetitorChange.objects.create(
        competitor=competitor_monitor,
        url="https://acme.example.com",
        change_type=CompetitorChange.ChangeType.NEW_PRODUCT,
    )
    rep = str(change)
    assert "Acme Competitor" in rep
    assert "new_product" in rep


@pytest.mark.django_db
def test_competitor_snapshot_ordering(competitor_monitor: CompetitorMonitor) -> None:
    """Snapshots are ordered by scraped_at descending."""
    CompetitorSnapshot.objects.create(
        competitor=competitor_monitor,
        url="https://example.com/1",
        content_hash="c" * 64,
    )
    CompetitorSnapshot.objects.create(
        competitor=competitor_monitor,
        url="https://example.com/2",
        content_hash="d" * 64,
    )
    snapshots = list(CompetitorSnapshot.objects.all())
    # Second one should be first (more recent)
    assert snapshots[0].url == "https://example.com/2"


# ---------------------------------------------------------------------------
# SentimentScore tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sentiment_score_creation(sentiment_score: SentimentScore) -> None:
    """SentimentScore can be created with all required fields."""
    assert sentiment_score.id is not None
    assert isinstance(sentiment_score.id, uuid.UUID)
    assert sentiment_score.tenant_id == "test-tenant-001"
    assert sentiment_score.text == "This product is amazing and works perfectly!"
    assert sentiment_score.overall_sentiment == "positive"
    assert sentiment_score.overall_score == Decimal("0.875")
    assert sentiment_score.confidence == Decimal("0.950")


@pytest.mark.django_db
def test_sentiment_score_str(sentiment_score: SentimentScore) -> None:
    """String representation includes sentiment and score."""
    rep = str(sentiment_score)
    assert "positive" in rep
    assert "0.875" in rep


@pytest.mark.django_db
def test_sentiment_score_defaults(tenant_id: str) -> None:
    """SentimentScore fields have correct defaults."""
    ss = SentimentScore.objects.create(
        tenant_id=tenant_id,
        text="Test text.",
        text_hash="hash123" * 8,
        overall_sentiment=SentimentScore.Sentiment.NEUTRAL,
        overall_score=Decimal("0.000"),
        confidence=Decimal("0.500"),
    )
    assert ss.model == SentimentScore.ModelType.AUTO
    assert ss.source_type == ""
    assert ss.source_id == ""
    assert ss.aspects == []
    assert ss.emotions == {}
    assert ss.language == "en"


@pytest.mark.django_db
def test_sentiment_score_all_sentiments(tenant_id: str) -> None:
    """All Sentiment choices can be stored."""
    for value, _label in SentimentScore.Sentiment.choices:
        ss = SentimentScore.objects.create(
            tenant_id=tenant_id,
            text=f"Text for {value}",
            text_hash=f"hash_{value}" + "0" * 50,
            overall_sentiment=value,
            overall_score=Decimal("0.500"),
            confidence=Decimal("0.900"),
        )
        assert ss.overall_sentiment == value


@pytest.mark.django_db
def test_sentiment_score_all_models(tenant_id: str) -> None:
    """All ModelType choices can be stored."""
    for value, _label in SentimentScore.ModelType.choices:
        ss = SentimentScore.objects.create(
            tenant_id=tenant_id,
            text=f"Text for {value}",
            text_hash=f"model_{value}" + "0" * 48,
            model=value,
            overall_sentiment=SentimentScore.Sentiment.POSITIVE,
            overall_score=Decimal("0.800"),
            confidence=Decimal("0.900"),
        )
        assert ss.model == value


@pytest.mark.django_db
def test_sentiment_score_aspects(tenant_id: str) -> None:
    """aspects JSON field stores aspect-based sentiments."""
    ss = SentimentScore.objects.create(
        tenant_id=tenant_id,
        text="The battery is great but the screen is poor.",
        text_hash="aspect_hash" + "0" * 51,
        overall_sentiment=SentimentScore.Sentiment.MIXED,
        overall_score=Decimal("0.100"),
        confidence=Decimal("0.850"),
        aspects=[
            {"aspect": "battery", "sentiment": "positive", "score": 0.9},
            {"aspect": "screen", "sentiment": "negative", "score": -0.7},
        ],
    )
    assert len(ss.aspects) == 2
    assert ss.aspects[0]["aspect"] == "battery"
    assert ss.aspects[1]["sentiment"] == "negative"


@pytest.mark.django_db
def test_sentiment_score_emotions(tenant_id: str) -> None:
    """emotions JSON field stores emotion scores."""
    ss = SentimentScore.objects.create(
        tenant_id=tenant_id,
        text="I am furious about this delay!",
        text_hash="emotion_hash" + "0" * 50,
        overall_sentiment=SentimentScore.Sentiment.NEGATIVE,
        overall_score=Decimal("-0.750"),
        confidence=Decimal("0.920"),
        emotions={"anger": 0.9, "frustration": 0.8, "sadness": 0.3},
    )
    assert ss.emotions["anger"] == 0.9
    assert ss.emotions["frustration"] == 0.8


@pytest.mark.django_db
def test_sentiment_score_negative_score(tenant_id: str) -> None:
    """overall_score can be negative for negative sentiment."""
    ss = SentimentScore.objects.create(
        tenant_id=tenant_id,
        text="Terrible experience, would not recommend.",
        text_hash="neg_hash" + "0" * 54,
        overall_sentiment=SentimentScore.Sentiment.NEGATIVE,
        overall_score=Decimal("-0.850"),
        confidence=Decimal("0.880"),
    )
    assert ss.overall_score == Decimal("-0.850")


@pytest.mark.django_db
def test_sentiment_score_language(tenant_id: str) -> None:
    """language field stores detected language code."""
    ss = SentimentScore.objects.create(
        tenant_id=tenant_id,
        text="Cette produit est excellent.",
        text_hash="fr_hash" + "0" * 55,
        overall_sentiment=SentimentScore.Sentiment.POSITIVE,
        overall_score=Decimal("0.900"),
        confidence=Decimal("0.870"),
        language="fr",
    )
    assert ss.language == "fr"
