"""Tests for Strategy models: AudiencePersona, CompetitorProfile, ContentStrategy."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.strategy.models import (
    AudiencePersona,
    CompetitorContent,
    CompetitorProfile,
    ContentStrategy,
    PersonaCampaignLink,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tenant_id() -> str:
    """Return a consistent tenant ID for tests."""
    return "test-tenant-001"


@pytest.fixture
def persona(tenant_id: str) -> AudiencePersona:
    """Create and return an AudiencePersona instance."""
    return AudiencePersona.objects.create(
        tenant_id=tenant_id,
        name="Marketing Mary",
        description="A marketing professional who loves automation tools.",
        demographics={
            "ageRange": "25-34",
            "gender": "female",
            "locations": ["US", "UK"],
            "incomeRange": "$75k-$100k",
            "education": "Bachelor's",
            "occupation": "Marketing Manager",
        },
        psychographics={
            "values": ["efficiency", "innovation"],
            "interests": ["tech", "marketing"],
            "lifestyle": "urban professional",
        },
        pain_points=["Too many tools", "Lack of integration"],
        content_preferences={
            "formats": ["video", "blog"],
            "topics": ["automation", "AI"],
            "tonePreference": "professional",
        },
        channel_preferences=[
            {"platform": "linkedin", "rank": 1, "engagementRate": 0.05},
            {"platform": "twitter", "rank": 2, "engagementRate": 0.03},
        ],
        is_active=True,
    )


@pytest.fixture
def competitor_profile(tenant_id: str) -> CompetitorProfile:
    """Create and return a CompetitorProfile instance."""
    return CompetitorProfile.objects.create(
        tenant_id=tenant_id,
        name="Acme Corp",
        website="https://acme.example.com",
        social_profiles={
            "instagram": {"handle": "@acme", "followers": 50000},
            "linkedin": {"handle": "acme-corp", "followers": 12000},
        },
        scraping_config={"frequency": "daily", "sources": ["blog", "social"]},
        is_active=True,
        swot_analysis={
            "strengths": ["Brand recognition", "Large team"],
            "weaknesses": ["Slow innovation"],
            "opportunities": ["AI integration"],
            "threats": ["New startups"],
        },
    )


@pytest.fixture
def content_strategy(tenant_id: str) -> ContentStrategy:
    """Create and return a ContentStrategy instance."""
    return ContentStrategy.objects.create(
        tenant_id=tenant_id,
        name="Q1 Growth Strategy",
        goal=ContentStrategy.Goal.LEAD_GENERATION,
        target_personas=["uuid-1", "uuid-2"],
        topic_clusters={
            "pillars": [{"topic": "AI in Marketing", "searchVolume": 5000, "difficulty": 45}],
            "clusters": [{"topic": "Marketing Automation", "parent": "AI in Marketing"}],
        },
        format_mix={
            "blog": 0.4,
            "video": 0.3,
            "social": 0.3,
        },
        channel_allocation={
            "organic_social": {"budget": 0.3, "effort": 0.4, "priority": "high"},
            "paid_search": {"budget": 0.5, "effort": 0.3, "priority": "high"},
        },
        content_pillars=[
            {"theme": "Education", "description": "Teach customers", "keywords": ["how-to"]},
        ],
        gap_analysis={
            "missingTopics": ["AI ethics"],
            "competitorCoverage": {"acme": 0.8},
            "opportunityScore": 75,
        },
    )


# ---------------------------------------------------------------------------
# AudiencePersona tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_persona_creation(persona: AudiencePersona) -> None:
    """AudiencePersona can be created with all required fields."""
    assert persona.id is not None
    assert isinstance(persona.id, uuid.UUID)
    assert persona.name == "Marketing Mary"
    assert persona.tenant_id == "test-tenant-001"
    assert persona.is_active is True


@pytest.mark.django_db
def test_persona_str(persona: AudiencePersona) -> None:
    """String representation returns the name."""
    assert str(persona) == "Marketing Mary"


@pytest.mark.django_db
def test_persona_default_active(tenant_id: str) -> None:
    """AudiencePersona defaults to active."""
    p = AudiencePersona.objects.create(
        tenant_id=tenant_id,
        name="Default Persona",
    )
    assert p.is_active is True


@pytest.mark.django_db
def test_persona_unique_name_per_tenant(tenant_id: str) -> None:
    """Duplicate persona name within same tenant raises IntegrityError."""
    AudiencePersona.objects.create(tenant_id=tenant_id, name="Unique Persona")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            AudiencePersona.objects.create(tenant_id=tenant_id, name="Unique Persona")


@pytest.mark.django_db
def test_persona_unique_name_different_tenants(tenant_id: str) -> None:
    """Same persona name in different tenants is allowed."""
    p1 = AudiencePersona.objects.create(tenant_id=tenant_id, name="Shared Persona")
    p2 = AudiencePersona.objects.create(tenant_id="other-tenant", name="Shared Persona")
    assert p1.id is not None
    assert p2.id is not None


@pytest.mark.django_db
def test_persona_json_fields(persona: AudiencePersona) -> None:
    """All JSON fields store and retrieve data correctly."""
    assert persona.demographics["ageRange"] == "25-34"
    assert persona.psychographics["values"] == ["efficiency", "innovation"]
    assert persona.pain_points == ["Too many tools", "Lack of integration"]
    assert persona.content_preferences["tonePreference"] == "professional"
    assert len(persona.channel_preferences) == 2
    assert persona.data_sources == []


@pytest.mark.django_db
def test_persona_campaign_link(persona: AudiencePersona) -> None:
    """PersonaCampaignLink connects a persona to a campaign with weight."""
    campaign_id = uuid.uuid4()
    link = PersonaCampaignLink.objects.create(
        persona=persona,
        campaign_id=campaign_id,
        weight=Decimal("0.75"),
    )
    assert link.id is not None
    assert link.persona == persona
    assert link.campaign_id == campaign_id
    assert link.weight == Decimal("0.75")


@pytest.mark.django_db
def test_persona_campaign_link_str(persona: AudiencePersona) -> None:
    """String representation includes persona name, campaign and weight."""
    campaign_id = uuid.uuid4()
    link = PersonaCampaignLink.objects.create(
        persona=persona,
        campaign_id=campaign_id,
        weight=Decimal("0.60"),
    )
    rep = str(link)
    assert "Marketing Mary" in rep
    assert "0.60" in rep


@pytest.mark.django_db
def test_persona_campaign_link_unique_together(
    persona: AudiencePersona,
) -> None:
    """Duplicate persona+campaign_id raises IntegrityError."""
    campaign_id = uuid.uuid4()
    PersonaCampaignLink.objects.create(persona=persona, campaign_id=campaign_id)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            PersonaCampaignLink.objects.create(persona=persona, campaign_id=campaign_id)


@pytest.mark.django_db
def test_persona_campaign_link_default_weight(persona: AudiencePersona) -> None:
    """PersonaCampaignLink defaults to weight 0.5."""
    link = PersonaCampaignLink.objects.create(
        persona=persona,
        campaign_id=uuid.uuid4(),
    )
    assert link.weight == Decimal("0.50")


# ---------------------------------------------------------------------------
# CompetitorProfile tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_competitor_profile_creation(competitor_profile: CompetitorProfile) -> None:
    """CompetitorProfile can be created with all required fields."""
    assert competitor_profile.id is not None
    assert isinstance(competitor_profile.id, uuid.UUID)
    assert competitor_profile.name == "Acme Corp"
    assert competitor_profile.tenant_id == "test-tenant-001"
    assert competitor_profile.is_active is True


@pytest.mark.django_db
def test_competitor_profile_str(competitor_profile: CompetitorProfile) -> None:
    """String representation returns the name."""
    assert str(competitor_profile) == "Acme Corp"


@pytest.mark.django_db
def test_competitor_profile_default_active(tenant_id: str) -> None:
    """CompetitorProfile defaults to active."""
    cp = CompetitorProfile.objects.create(
        tenant_id=tenant_id,
        name="New Competitor",
    )
    assert cp.is_active is True
    assert cp.swot_analysis == {}
    assert cp.scraping_config == {}
    assert cp.social_profiles == {}


@pytest.mark.django_db
def test_competitor_profile_unique_name_per_tenant(tenant_id: str) -> None:
    """Duplicate competitor name within same tenant raises IntegrityError."""
    CompetitorProfile.objects.create(tenant_id=tenant_id, name="Unique Competitor")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CompetitorProfile.objects.create(tenant_id=tenant_id, name="Unique Competitor")


@pytest.mark.django_db
def test_competitor_profile_json_fields(competitor_profile: CompetitorProfile) -> None:
    """All JSON fields store and retrieve data correctly."""
    assert competitor_profile.social_profiles["instagram"]["followers"] == 50000
    assert competitor_profile.scraping_config["frequency"] == "daily"
    assert competitor_profile.swot_analysis["strengths"] == ["Brand recognition", "Large team"]


@pytest.mark.django_db
def test_competitor_content(
    competitor_profile: CompetitorProfile,
) -> None:
    """CompetitorContent stores scraped content with engagement metrics."""
    content = CompetitorContent.objects.create(
        competitor=competitor_profile,
        platform="instagram",
        content_type="post",
        text="Check out our new product!",
        media_urls=["https://cdn.example.com/img1.jpg"],
        engagement_metrics={"likes": 1200, "shares": 300, "comments": 150},
        topics=["product-launch", "innovation"],
        sentiment=Decimal("0.75"),
    )
    assert content.id is not None
    assert content.competitor == competitor_profile
    assert content.platform == "instagram"
    assert content.sentiment == Decimal("0.75")


@pytest.mark.django_db
def test_competitor_content_str(competitor_profile: CompetitorProfile) -> None:
    """String representation includes competitor name, platform and type."""
    content = CompetitorContent.objects.create(
        competitor=competitor_profile,
        platform="linkedin",
        content_type="article",
        text="Our industry insights.",
    )
    rep = str(content)
    assert "Acme Corp" in rep
    assert "linkedin" in rep
    assert "article" in rep


@pytest.mark.django_db
def test_competitor_content_sentiment_range(
    competitor_profile: CompetitorProfile,
) -> None:
    """Sentiment score can be negative."""
    content = CompetitorContent.objects.create(
        competitor=competitor_profile,
        platform="twitter",
        content_type="post",
        text="Complaint about service.",
        sentiment=Decimal("-0.45"),
    )
    assert content.sentiment == Decimal("-0.45")


# ---------------------------------------------------------------------------
# ContentStrategy tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_content_strategy_creation(content_strategy: ContentStrategy) -> None:
    """ContentStrategy can be created with all required fields."""
    assert content_strategy.id is not None
    assert isinstance(content_strategy.id, uuid.UUID)
    assert content_strategy.name == "Q1 Growth Strategy"
    assert content_strategy.goal == "lead_generation"
    assert content_strategy.tenant_id == "test-tenant-001"


@pytest.mark.django_db
def test_content_strategy_str(content_strategy: ContentStrategy) -> None:
    """String representation includes name and goal."""
    assert str(content_strategy) == "Q1 Growth Strategy (lead_generation)"


@pytest.mark.django_db
def test_content_strategy_all_goals(tenant_id: str) -> None:
    """All Goal choices can be stored."""
    for idx, (value, _label) in enumerate(ContentStrategy.Goal.choices):
        cs = ContentStrategy.objects.create(
            tenant_id=tenant_id,
            name=f"Strategy {idx}",
            goal=value,
        )
        assert cs.goal == value


@pytest.mark.django_db
def test_content_strategy_blank_goal(tenant_id: str) -> None:
    """ContentStrategy goal can be blank."""
    cs = ContentStrategy.objects.create(
        tenant_id=tenant_id,
        name="No Goal Strategy",
        goal="",
    )
    assert cs.goal == ""


@pytest.mark.django_db
def test_content_strategy_json_fields(content_strategy: ContentStrategy) -> None:
    """All JSON fields store and retrieve data correctly."""
    assert content_strategy.target_personas == ["uuid-1", "uuid-2"]
    assert content_strategy.topic_clusters["pillars"][0]["topic"] == "AI in Marketing"
    assert content_strategy.format_mix["blog"] == 0.4
    assert content_strategy.channel_allocation["paid_search"]["priority"] == "high"
    assert len(content_strategy.content_pillars) == 1
    assert content_strategy.gap_analysis["opportunityScore"] == 75


@pytest.mark.django_db
def test_content_strategy_default_json_fields(tenant_id: str) -> None:
    """JSON fields default to empty collections."""
    cs = ContentStrategy.objects.create(
        tenant_id=tenant_id,
        name="Minimal Strategy",
    )
    assert cs.target_personas == []
    assert cs.topic_clusters == {}
    assert cs.format_mix == {}
    assert cs.channel_allocation == {}
    assert cs.content_pillars == []
    assert cs.gap_analysis == {}
