"""Tests for Content Creation models: ContentGeneration, BrandKit, ContentTemplate, ABTest."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from apps.content_creation.models import ABTest, BrandKit, ContentGeneration, ContentTemplate

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tenant_id() -> str:
    """Return a consistent tenant ID for tests."""
    return "test-tenant-001"


@pytest.fixture
def content_generation(tenant_id: str) -> ContentGeneration:
    """Create and return a ContentGeneration instance."""
    return ContentGeneration.objects.create(
        tenant_id=tenant_id,
        title="Test Blog Post",
        prompt="Write a blog about testing",
        content_type=ContentGeneration.ContentType.TEXT,
        status=ContentGeneration.Status.DRAFT,
        body_text="This is the generated content.",
        model_used="gpt-4o",
        tokens_used=150,
        generation_time_ms=2500,
        created_by="user-001",
    )


@pytest.fixture
def brand_kit(tenant_id: str) -> BrandKit:
    """Create and return a BrandKit instance."""
    return BrandKit.objects.create(
        tenant_id=tenant_id,
        name="Test Brand",
        description="Brand for testing",
        voice=BrandKit.Voice.PROFESSIONAL,
        forbidden_words=["badword", "worse"],
        required_phrases=["quality first"],
        color_palette=[{"name": "Primary", "hex": "#FF0000"}],
        min_readability=Decimal("60.00"),
        min_compliance_score=80,
    )


@pytest.fixture
def content_template(tenant_id: str) -> ContentTemplate:
    """Create and return a ContentTemplate instance."""
    return ContentTemplate.objects.create(
        tenant_id=tenant_id,
        name="Blog Template",
        description="Standard blog post template",
        category=ContentTemplate.Category.BLOG,
        content_type=ContentTemplate.ContentType.TEXT,
        body="Hello {{ name }}, welcome to {{ company }}!",
        variables=[
            {"name": "name", "type": "string", "required": True},
            {"name": "company", "type": "string", "required": True},
        ],
        default_values={"name": "Reader"},
        created_by="user-001",
    )


@pytest.fixture
def ab_test(tenant_id: str) -> ABTest:
    """Create and return an ABTest instance."""
    return ABTest.objects.create(
        tenant_id=tenant_id,
        name="Headline Test",
        content_generation_id=uuid.uuid4(),
        variants=[
            {"id": "A", "headline": "Original"},
            {"id": "B", "headline": "Variation"},
        ],
        status=ABTest.Status.DRAFT,
        winner_criteria=ABTest.WinnerCriteria.CTR,
        sample_size=1000,
    )


# ---------------------------------------------------------------------------
# ContentGeneration tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_content_generation_creation(content_generation: ContentGeneration) -> None:
    """ContentGeneration can be created with all required fields."""
    assert content_generation.id is not None
    assert isinstance(content_generation.id, uuid.UUID)
    assert content_generation.title == "Test Blog Post"
    assert content_generation.prompt == "Write a blog about testing"
    assert content_generation.content_type == "text"
    assert content_generation.status == "draft"
    assert content_generation.body_text == "This is the generated content."
    assert content_generation.model_used == "gpt-4o"
    assert content_generation.tokens_used == 150
    assert content_generation.generation_time_ms == 2500
    assert content_generation.created_by == "user-001"


@pytest.mark.django_db
def test_content_generation_str(content_generation: ContentGeneration) -> None:
    """String representation includes title, content type and status."""
    assert str(content_generation) == "Test Blog Post (text) -- draft"


@pytest.mark.django_db
def test_content_generation_default_status(tenant_id: str) -> None:
    """ContentGeneration defaults to DRAFT status."""
    cg = ContentGeneration.objects.create(
        tenant_id=tenant_id,
        title="Default Status Post",
        prompt="Testing defaults",
        content_type=ContentGeneration.ContentType.TEXT,
        created_by="user-001",
    )
    assert cg.status == ContentGeneration.Status.DRAFT


@pytest.mark.django_db
def test_content_generation_all_content_types(tenant_id: str) -> None:
    """All ContentType choices can be stored."""
    for value, _label in ContentGeneration.ContentType.choices:
        cg = ContentGeneration.objects.create(
            tenant_id=tenant_id,
            title=f"Post {value}",
            prompt="Test",
            content_type=value,
            created_by="user-001",
        )
        assert cg.content_type == value


@pytest.mark.django_db
def test_content_generation_scoring_fields(tenant_id: str) -> None:
    """Scoring fields (readability, engagement, brand compliance, SEO) can be set."""
    cg = ContentGeneration.objects.create(
        tenant_id=tenant_id,
        title="Scored Post",
        prompt="Test",
        content_type=ContentGeneration.ContentType.TEXT,
        readability_score=Decimal("75.50"),
        engagement_prediction=Decimal("82.00"),
        brand_compliance_score=Decimal("90.00"),
        seo_score=Decimal("68.00"),
        created_by="user-001",
    )
    assert cg.readability_score == Decimal("75.50")
    assert cg.engagement_prediction == Decimal("82.00")
    assert cg.brand_compliance_score == Decimal("90.00")
    assert cg.seo_score == Decimal("68.00")


@pytest.mark.django_db
def test_content_generation_nullable_fields(tenant_id: str) -> None:
    """Nullable fields (tokens_used, generation_time_ms) can be None."""
    cg = ContentGeneration.objects.create(
        tenant_id=tenant_id,
        title="Nullable Post",
        prompt="Test",
        content_type=ContentGeneration.ContentType.TEXT,
        tokens_used=None,
        generation_time_ms=None,
        created_by="user-001",
    )
    assert cg.tokens_used is None
    assert cg.generation_time_ms is None


@pytest.mark.django_db
def test_content_generation_media_urls(tenant_id: str) -> None:
    """media_urls JSON field stores a list of URLs."""
    urls = ["https://cdn.example.com/img1.jpg", "https://cdn.example.com/img2.jpg"]
    cg = ContentGeneration.objects.create(
        tenant_id=tenant_id,
        title="Media Post",
        prompt="Test",
        content_type=ContentGeneration.ContentType.IMAGE,
        media_urls=urls,
        created_by="user-001",
    )
    assert cg.media_urls == urls


@pytest.mark.django_db
def test_content_generation_default_media_urls(tenant_id: str) -> None:
    """media_urls defaults to an empty list."""
    cg = ContentGeneration.objects.create(
        tenant_id=tenant_id,
        title="No Media Post",
        prompt="Test",
        content_type=ContentGeneration.ContentType.TEXT,
        created_by="user-001",
    )
    assert cg.media_urls == []


# ---------------------------------------------------------------------------
# BrandKit tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_brand_kit_creation(brand_kit: BrandKit) -> None:
    """BrandKit can be created with all fields."""
    assert brand_kit.id is not None
    assert isinstance(brand_kit.id, uuid.UUID)
    assert brand_kit.name == "Test Brand"
    assert brand_kit.description == "Brand for testing"
    assert brand_kit.voice == "professional"
    assert brand_kit.forbidden_words == ["badword", "worse"]
    assert brand_kit.required_phrases == ["quality first"]
    assert len(brand_kit.color_palette) == 1


@pytest.mark.django_db
def test_brand_kit_str(brand_kit: BrandKit) -> None:
    """String representation returns the name."""
    assert str(brand_kit) == "Test Brand"


@pytest.mark.django_db
def test_brand_kit_default_voice(tenant_id: str) -> None:
    """BrandKit defaults to PROFESSIONAL voice."""
    bk = BrandKit.objects.create(
        tenant_id=tenant_id,
        name="Default Voice Brand",
    )
    assert bk.voice == BrandKit.Voice.PROFESSIONAL


@pytest.mark.django_db
def test_brand_kit_all_voices(tenant_id: str) -> None:
    """All Voice choices can be stored."""
    for idx, (value, _label) in enumerate(BrandKit.Voice.choices):
        bk = BrandKit.objects.create(
            tenant_id=tenant_id,
            name=f"Brand {idx}",
            voice=value,
        )
        assert bk.voice == value


@pytest.mark.django_db
def test_brand_kit_default_scores(tenant_id: str) -> None:
    """BrandKit defaults to correct score values."""
    bk = BrandKit.objects.create(
        tenant_id=tenant_id,
        name="Default Scores",
    )
    assert bk.min_readability == Decimal("60.00")
    assert bk.min_compliance_score == 75


@pytest.mark.django_db
def test_brand_kit_json_fields_blank(tenant_id: str) -> None:
    """All JSON fields default to empty collections."""
    bk = BrandKit.objects.create(
        tenant_id=tenant_id,
        name="Minimal Brand",
    )
    assert bk.tone_rules == []
    assert bk.forbidden_words == []
    assert bk.required_phrases == []
    assert bk.color_palette == []
    assert bk.competitor_list == []
    assert bk.avoid_topics == []
    assert bk.target_audience == {}
    assert bk.font_preferences == {}


# ---------------------------------------------------------------------------
# ContentTemplate tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_content_template_creation(content_template: ContentTemplate) -> None:
    """ContentTemplate can be created with all fields."""
    assert content_template.id is not None
    assert isinstance(content_template.id, uuid.UUID)
    assert content_template.name == "Blog Template"
    assert content_template.category == "blog"
    assert content_template.content_type == "text"
    assert content_template.body == "Hello {{ name }}, welcome to {{ company }}!"
    assert len(content_template.variables) == 2


@pytest.mark.django_db
def test_content_template_str(content_template: ContentTemplate) -> None:
    """String representation includes name and category."""
    assert str(content_template) == "Blog Template (blog)"


@pytest.mark.django_db
def test_content_template_default_values(tenant_id: str) -> None:
    """ContentTemplate fields have correct defaults."""
    ct = ContentTemplate.objects.create(
        tenant_id=tenant_id,
        name="Default Template",
        body="Simple body",
    )
    assert ct.content_type == ContentTemplate.ContentType.TEXT
    assert ct.usage_count == 0
    assert ct.is_public is False
    assert ct.variables == []
    assert ct.default_values == {}


@pytest.mark.django_db
def test_content_template_is_public(tenant_id: str) -> None:
    """A template can be marked as public."""
    ct = ContentTemplate.objects.create(
        tenant_id=tenant_id,
        name="Public Template",
        body="Shared body",
        is_public=True,
    )
    assert ct.is_public is True


@pytest.mark.django_db
def test_content_template_all_categories(tenant_id: str) -> None:
    """All Category choices can be stored."""
    for idx, (value, _label) in enumerate(ContentTemplate.Category.choices):
        ct = ContentTemplate.objects.create(
            tenant_id=tenant_id,
            name=f"Template {idx}",
            body="Body",
            category=value,
        )
        assert ct.category == value


@pytest.mark.django_db
def test_content_template_usage_count_increment(tenant_id: str) -> None:
    """usage_count can be incremented."""
    ct = ContentTemplate.objects.create(
        tenant_id=tenant_id,
        name="Used Template",
        body="Body",
        usage_count=5,
    )
    ct.usage_count += 1
    ct.save()
    ct.refresh_from_db()
    assert ct.usage_count == 6


# ---------------------------------------------------------------------------
# ABTest tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ab_test_creation(ab_test: ABTest) -> None:
    """ABTest can be created with all required fields."""
    assert ab_test.id is not None
    assert isinstance(ab_test.id, uuid.UUID)
    assert ab_test.name == "Headline Test"
    assert ab_test.status == ABTest.Status.DRAFT
    assert ab_test.winner_criteria == ABTest.WinnerCriteria.CTR
    assert ab_test.sample_size == 1000
    assert len(ab_test.variants) == 2


@pytest.mark.django_db
def test_ab_test_str(ab_test: ABTest) -> None:
    """String representation includes name and status."""
    assert str(ab_test) == "Headline Test (draft)"


@pytest.mark.django_db
def test_ab_test_default_status(tenant_id: str) -> None:
    """ABTest defaults to DRAFT status."""
    test = ABTest.objects.create(
        tenant_id=tenant_id,
        name="Default Test",
        content_generation_id=uuid.uuid4(),
    )
    assert test.status == ABTest.Status.DRAFT
    assert test.winner_criteria == ABTest.WinnerCriteria.CTR


@pytest.mark.django_db
def test_ab_test_all_statuses(tenant_id: str) -> None:
    """All Status choices can be stored."""
    for idx, (value, _label) in enumerate(ABTest.Status.choices):
        test = ABTest.objects.create(
            tenant_id=tenant_id,
            name=f"Test {idx}",
            content_generation_id=uuid.uuid4(),
            status=value,
        )
        assert test.status == value


@pytest.mark.django_db
def test_ab_test_all_winner_criteria(tenant_id: str) -> None:
    """All WinnerCriteria choices can be stored."""
    for idx, (value, _label) in enumerate(ABTest.WinnerCriteria.choices):
        test = ABTest.objects.create(
            tenant_id=tenant_id,
            name=f"Test {idx}",
            content_generation_id=uuid.uuid4(),
            winner_criteria=value,
        )
        assert test.winner_criteria == value


@pytest.mark.django_db
def test_ab_test_results_json(tenant_id: str) -> None:
    """ABTest results JSON field stores statistical results."""
    test = ABTest.objects.create(
        tenant_id=tenant_id,
        name="Results Test",
        content_generation_id=uuid.uuid4(),
        results={
            "winner": "B",
            "confidence": 0.95,
            "p_value": 0.02,
            "variant_a_ctr": 0.05,
            "variant_b_ctr": 0.08,
        },
    )
    assert test.results["winner"] == "B"
    assert test.results["confidence"] == 0.95


@pytest.mark.django_db
def test_ab_test_nullable_dates(tenant_id: str) -> None:
    """ABTest start_date and end_date can be None."""
    test = ABTest.objects.create(
        tenant_id=tenant_id,
        name="No Dates Test",
        content_generation_id=uuid.uuid4(),
    )
    assert test.start_date is None
    assert test.end_date is None
