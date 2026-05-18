"""Tests for Campaigns models: Campaign, CampaignChannel, CampaignBudget."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.campaigns.models import Campaign, CampaignBudget, CampaignChannel
from apps.clients.models import Client

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tenant_id() -> str:
    """Return a consistent tenant ID for tests."""
    return "test-tenant-001"


@pytest.fixture
def client(tenant_id: str) -> Client:
    """Create and return a Client instance."""
    return Client.objects.create(
        tenant_id=tenant_id,
        name="Test Client",
        slug="test-client",
        industry="Technology",
        status=Client.Status.ACTIVE,
        tier=Client.Tier.PRO,
    )


@pytest.fixture
def campaign(client: Client, tenant_id: str) -> Campaign:
    """Create and return a Campaign instance."""
    return Campaign.objects.create(
        tenant_id=tenant_id,
        client=client,
        name="Summer Sale 2024",
        description="Our biggest summer sale campaign",
        objective=Campaign.Objective.CONVERSION,
        stage=Campaign.Stage.PLANNING,
        status=Campaign.Status.DRAFT,
        budget=Decimal("50000.00"),
        currency="USD",
        pacing_type=Campaign.PacingType.EVEN,
        attribution_model=Campaign.AttributionModel.LAST_TOUCH,
        created_by="user-001",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
    )


@pytest.fixture
def campaign_channel(campaign: Campaign) -> CampaignChannel:
    """Create and return a CampaignChannel instance."""
    return CampaignChannel.objects.create(
        campaign=campaign,
        channel_type=CampaignChannel.ChannelType.PAID_SOCIAL,
        platform="meta_ads",
        config={"audience": "lookalike", "budget_split": 0.6},
        daily_budget=Decimal("500.00"),
        status=CampaignChannel.Status.ACTIVE,
    )


@pytest.fixture
def campaign_budget(campaign: Campaign) -> CampaignBudget:
    """Create and return a CampaignBudget allocation entry."""
    return CampaignBudget.objects.create(
        campaign=campaign,
        amount=Decimal("50000.00"),
        type=CampaignBudget.EntryType.ALLOCATION,
        channel="meta_ads",
        description="Initial budget allocation",
    )


# ---------------------------------------------------------------------------
# Campaign tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_campaign_creation(campaign: Campaign) -> None:
    """Campaign can be created with all required fields."""
    assert campaign.id is not None
    assert campaign.name == "Summer Sale 2024"
    assert campaign.description == "Our biggest summer sale campaign"
    assert campaign.objective == "conversion"
    assert campaign.stage == "planning"
    assert campaign.status == "draft"
    assert campaign.budget == Decimal("50000.00")
    assert campaign.currency == "USD"
    assert campaign.pacing_type == "even"
    assert campaign.attribution_model == "last_touch"
    assert campaign.created_by == "user-001"


@pytest.mark.django_db
def test_campaign_str(campaign: Campaign) -> None:
    """String representation includes name and stage."""
    assert str(campaign) == "Summer Sale 2024 (planning)"


@pytest.mark.django_db
def test_campaign_defaults(client: Client, tenant_id: str) -> None:
    """Campaign fields have correct defaults."""
    c = Campaign.objects.create(
        tenant_id=tenant_id,
        client=client,
        name="Minimal Campaign",
    )
    assert c.objective == Campaign.Objective.AWARENESS
    assert c.stage == Campaign.Stage.PLANNING
    assert c.status == Campaign.Status.DRAFT
    assert c.currency == "USD"
    assert c.pacing_type == Campaign.PacingType.EVEN
    assert c.attribution_model == Campaign.AttributionModel.LAST_TOUCH
    assert c.current_spend == Decimal("0.00")
    assert c.brief_approved is False
    assert c.all_creatives_approved is False
    assert c.all_platforms_published is False


@pytest.mark.django_db
def test_campaign_all_objectives(client: Client, tenant_id: str) -> None:
    """All Objective choices can be stored."""
    for idx, (value, _label) in enumerate(Campaign.Objective.choices):
        c = Campaign.objects.create(
            tenant_id=tenant_id,
            client=client,
            name=f"Campaign {idx}",
            objective=value,
        )
        assert c.objective == value


@pytest.mark.django_db
def test_campaign_all_stages(client: Client, tenant_id: str) -> None:
    """All Stage choices can be stored."""
    for idx, (value, _label) in enumerate(Campaign.Stage.choices):
        c = Campaign.objects.create(
            tenant_id=tenant_id,
            client=client,
            name=f"Campaign {idx}",
            stage=value,
        )
        assert c.stage == value


@pytest.mark.django_db
def test_campaign_all_statuses(client: Client, tenant_id: str) -> None:
    """All Status choices can be stored."""
    for idx, (value, _label) in enumerate(Campaign.Status.choices):
        c = Campaign.objects.create(
            tenant_id=tenant_id,
            client=client,
            name=f"Campaign {idx}",
            status=value,
        )
        assert c.status == value


@pytest.mark.django_db
def test_campaign_spend_percentage(campaign: Campaign) -> None:
    """spend_percentage returns correct percentage."""
    campaign.current_spend = Decimal("12500.00")
    campaign.save()
    assert campaign.spend_percentage == 25.0


@pytest.mark.django_db
def test_campaign_spend_percentage_no_budget(client: Client, tenant_id: str) -> None:
    """spend_percentage returns 0.0 when budget is None."""
    c = Campaign.objects.create(
        tenant_id=tenant_id,
        client=client,
        name="No Budget",
        budget=None,
    )
    assert c.spend_percentage == 0.0


@pytest.mark.django_db
def test_campaign_spend_percentage_zero_budget(
    client: Client,
    tenant_id: str,
) -> None:
    """spend_percentage returns 0.0 when budget is zero."""
    c = Campaign.objects.create(
        tenant_id=tenant_id,
        client=client,
        name="Zero Budget",
        budget=Decimal("0.00"),
    )
    assert c.spend_percentage == 0.0


@pytest.mark.django_db
def test_campaign_days_remaining(campaign: Campaign) -> None:
    """days_remaining returns correct number of days."""
    assert campaign.days_remaining is not None
    assert campaign.days_remaining >= 29


@pytest.mark.django_db
def test_campaign_days_remaining_none(client: Client, tenant_id: str) -> None:
    """days_remaining returns None when end_date is not set."""
    c = Campaign.objects.create(
        tenant_id=tenant_id,
        client=client,
        name="No End Date",
        end_date=None,
    )
    assert c.days_remaining is None


@pytest.mark.django_db
def test_campaign_days_elapsed(campaign: Campaign) -> None:
    """days_elapsed returns 0 for a campaign starting today."""
    assert campaign.days_elapsed == 0


@pytest.mark.django_db
def test_campaign_parent_child(
    client: Client,
    tenant_id: str,
) -> None:
    """A campaign can have a parent campaign."""
    parent = Campaign.objects.create(
        tenant_id=tenant_id,
        client=client,
        name="Parent Campaign",
    )
    child = Campaign.objects.create(
        tenant_id=tenant_id,
        client=client,
        name="Child Campaign",
        parent_campaign=parent,
    )
    assert child.parent_campaign == parent
    assert parent.child_campaigns.count() == 1
    assert parent.child_campaigns.first() == child


@pytest.mark.django_db
def test_campaign_cloned_from(
    client: Client,
    tenant_id: str,
) -> None:
    """A campaign can be cloned from another."""
    original = Campaign.objects.create(
        tenant_id=tenant_id,
        client=client,
        name="Original Campaign",
    )
    clone = Campaign.objects.create(
        tenant_id=tenant_id,
        client=client,
        name="Cloned Campaign",
        cloned_from=original,
    )
    assert clone.cloned_from == original
    assert original.clones.count() == 1


@pytest.mark.django_db
def test_campaign_related_client(client: Client, tenant_id: str) -> None:
    """Campaign is linked to client via foreign key."""
    c = Campaign.objects.create(
        tenant_id=tenant_id,
        client=client,
        name="Linked Campaign",
    )
    assert c.client == client


# ---------------------------------------------------------------------------
# CampaignChannel tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_campaign_channel_creation(campaign_channel: CampaignChannel) -> None:
    """CampaignChannel can be created with all required fields."""
    assert campaign_channel.id is not None
    assert campaign_channel.channel_type == "paid_social"
    assert campaign_channel.platform == "meta_ads"
    assert campaign_channel.config == {"audience": "lookalike", "budget_split": 0.6}
    assert campaign_channel.daily_budget == Decimal("500.00")
    assert campaign_channel.status == "active"


@pytest.mark.django_db
def test_campaign_channel_str(campaign_channel: CampaignChannel) -> None:
    """String representation includes channel type, platform and campaign name."""
    rep = str(campaign_channel)
    assert "paid_social" in rep
    assert "meta_ads" in rep
    assert "Summer Sale 2024" in rep


@pytest.mark.django_db
def test_campaign_channel_defaults(campaign: Campaign) -> None:
    """CampaignChannel fields have correct defaults."""
    ch = CampaignChannel.objects.create(
        campaign=campaign,
        channel_type=CampaignChannel.ChannelType.ORGANIC_SOCIAL,
        platform="instagram",
    )
    assert ch.config == {}
    assert ch.daily_budget is None
    assert ch.total_spend == Decimal("0.00")
    assert ch.status == CampaignChannel.Status.PENDING
    assert ch.lead_time_days == 0
    assert ch.dependencies == []


@pytest.mark.django_db
def test_campaign_channel_all_types(campaign: Campaign) -> None:
    """All ChannelType choices can be stored."""
    for idx, (value, _label) in enumerate(CampaignChannel.ChannelType.choices):
        ch = CampaignChannel.objects.create(
            campaign=campaign,
            channel_type=value,
            platform=f"platform_{idx}",
        )
        assert ch.channel_type == value


@pytest.mark.django_db
def test_campaign_channel_all_statuses(campaign: Campaign) -> None:
    """All Status choices can be stored."""
    for idx, (value, _label) in enumerate(CampaignChannel.Status.choices):
        ch = CampaignChannel.objects.create(
            campaign=campaign,
            channel_type=CampaignChannel.ChannelType.EMAIL,
            platform="sendgrid",
            status=value,
        )
        assert ch.status == value


@pytest.mark.django_db
def test_campaign_channel_roas(campaign_channel: CampaignChannel) -> None:
    """roas property returns value from config."""
    campaign_channel.config = {"roas": 3.5}
    campaign_channel.save()
    assert campaign_channel.roas == 3.5


@pytest.mark.django_db
def test_campaign_channel_roas_default(campaign: Campaign) -> None:
    """roas property returns 0.0 when not in config."""
    ch = CampaignChannel.objects.create(
        campaign=campaign,
        channel_type=CampaignChannel.ChannelType.DISPLAY,
        platform="google_display",
    )
    assert ch.roas == 0.0


@pytest.mark.django_db
def test_campaign_channel_conversions(campaign_channel: CampaignChannel) -> None:
    """conversions property returns value from config."""
    campaign_channel.config = {"conversions": 150}
    campaign_channel.save()
    assert campaign_channel.conversions == 150


@pytest.mark.django_db
def test_campaign_channel_unique_constraint(campaign: Campaign) -> None:
    """Duplicate campaign+channel_type+platform raises IntegrityError."""
    CampaignChannel.objects.create(
        campaign=campaign,
        channel_type=CampaignChannel.ChannelType.SEO,
        platform="google",
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CampaignChannel.objects.create(
                campaign=campaign,
                channel_type=CampaignChannel.ChannelType.SEO,
                platform="google",
            )


# ---------------------------------------------------------------------------
# CampaignBudget tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_campaign_budget_creation(campaign_budget: CampaignBudget) -> None:
    """CampaignBudget can be created with all required fields."""
    assert campaign_budget.id is not None
    assert campaign_budget.amount == Decimal("50000.00")
    assert campaign_budget.type == "allocation"
    assert campaign_budget.channel == "meta_ads"
    assert campaign_budget.description == "Initial budget allocation"


@pytest.mark.django_db
def test_campaign_budget_str(campaign_budget: CampaignBudget) -> None:
    """String representation includes type, amount and campaign name."""
    rep = str(campaign_budget)
    assert "allocation" in rep
    assert "50000.00" in rep
    assert "Summer Sale 2024" in rep


@pytest.mark.django_db
def test_campaign_budget_is_allocation(campaign_budget: CampaignBudget) -> None:
    """is_allocation returns True for allocation entries."""
    assert campaign_budget.is_allocation is True


@pytest.mark.django_db
def test_campaign_budget_is_spend(campaign: Campaign) -> None:
    """is_spend returns True for spend entries."""
    spend = CampaignBudget.objects.create(
        campaign=campaign,
        amount=Decimal("-2500.00"),
        type=CampaignBudget.EntryType.SPEND,
    )
    assert spend.is_spend is True
    assert spend.is_allocation is False


@pytest.mark.django_db
def test_campaign_budget_all_entry_types(campaign: Campaign) -> None:
    """All EntryType choices can be stored."""
    for idx, (value, _label) in enumerate(CampaignBudget.EntryType.choices):
        entry = CampaignBudget.objects.create(
            campaign=campaign,
            amount=Decimal(f"{idx * 100}.00"),
            type=value,
        )
        assert entry.type == value


@pytest.mark.django_db
def test_campaign_budget_metadata_json(campaign: Campaign) -> None:
    """metadata JSON field stores additional context."""
    entry = CampaignBudget.objects.create(
        campaign=campaign,
        amount=Decimal("1000.00"),
        type=CampaignBudget.EntryType.SPEND,
        metadata={"roas": 2.5, "cpa": 10.0, "impressions": 50000},
    )
    assert entry.metadata["roas"] == 2.5
    assert entry.metadata["impressions"] == 50000


@pytest.mark.django_db
def test_campaign_budget_ordering(campaign: Campaign) -> None:
    """CampaignBudget entries are ordered by created_at descending."""
    CampaignBudget.objects.create(
        campaign=campaign,
        amount=Decimal("1000.00"),
        type=CampaignBudget.EntryType.ALLOCATION,
    )
    CampaignBudget.objects.create(
        campaign=campaign,
        amount=Decimal("2000.00"),
        type=CampaignBudget.EntryType.SPEND,
    )
    entries = list(CampaignBudget.objects.all())
    assert len(entries) == 2
    assert entries[0].amount == Decimal("2000.00")
    assert entries[1].amount == Decimal("1000.00")


@pytest.mark.django_db
def test_campaign_budget_related_to_campaign(campaign_budget: CampaignBudget) -> None:
    """CampaignBudget is linked to Campaign via foreign key."""
    assert campaign_budget.campaign.name == "Summer Sale 2024"
    assert campaign_budget in list(campaign_budget.campaign.budget_entries.all())
