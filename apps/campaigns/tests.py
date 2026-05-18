"""Campaign management tests.

Tests for campaign CRUD, lifecycle transitions, budget management,
A/B testing, performance tracking, and brief generation.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.campaigns.models import (
    Campaign,
    CampaignABTest,
    CampaignBudget,
    CampaignChannel,
)
from apps.campaigns.services.ab_testing import calculate_sample_size
from apps.campaigns.services.budget import calculate_pacing
from apps.campaigns.services.channels import (
    get_channel_recommendations,
    has_cycle,
    topological_sort,
)
from apps.campaigns.services.lifecycle import (
    get_available_stages,
    validate_transition,
)


@pytest.mark.django_db
class TestCampaignModel:
    """Tests for Campaign model."""

    def test_campaign_create(self, client_instance):
        campaign = Campaign.objects.create(
            tenant_id="test_tenant",
            client=client_instance,
            name="Test Campaign",
            objective=Campaign.Objective.CONVERSION,
            budget=Decimal("10000.00"),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )
        assert campaign.id is not None
        assert campaign.stage == Campaign.Stage.PLANNING
        assert campaign.status == Campaign.Status.DRAFT

    def test_campaign_spend_percentage(self, campaign_instance):
        campaign_instance.budget = Decimal("1000.00")
        campaign_instance.current_spend = Decimal("250.00")
        assert campaign_instance.spend_percentage == 25.0

    def test_campaign_days_remaining(self, campaign_instance):
        campaign_instance.end_date = date.today() + timedelta(days=10)
        assert campaign_instance.days_remaining == 10


@pytest.mark.django_db
class TestCampaignChannelModel:
    """Tests for CampaignChannel model."""

    def test_channel_create(self, campaign_instance):
        channel = CampaignChannel.objects.create(
            campaign=campaign_instance,
            channel_type=CampaignChannel.ChannelType.PAID_SEARCH,
            platform="google_ads",
            config={"keywords": ["test"]},
        )
        assert channel.id is not None
        assert channel.channel_type == "paid_search"


@pytest.mark.django_db
class TestCampaignABTestModel:
    """Tests for CampaignABTest model."""

    def test_ab_test_create(self, campaign_instance):
        test = CampaignABTest.objects.create(
            campaign=campaign_instance,
            name="Subject Line Test",
            test_type=CampaignABTest.TestType.SUBJECT_LINE,
            method=CampaignABTest.Method.FREQUENTIST,
            baseline_rate=Decimal("0.05"),
            minimum_detectable_effect=Decimal("0.20"),
        )
        assert test.id is not None
        assert test.status == CampaignABTest.Status.DRAFT


@pytest.mark.django_db
class TestCampaignBudgetModel:
    """Tests for CampaignBudget model."""

    def test_budget_entry_create(self, campaign_instance):
        entry = CampaignBudget.objects.create(
            campaign=campaign_instance,
            amount=Decimal("-500.00"),
            type=CampaignBudget.EntryType.SPEND,
            channel="google_ads",
            description="Daily ad spend",
        )
        assert entry.id is not None
        assert entry.is_spend is True
        assert entry.is_allocation is False


@pytest.mark.django_db
class TestLifecycleService:
    """Tests for lifecycle service."""

    def test_validate_transition_planning_to_brief(self, campaign_instance):
        # Fill required fields
        campaign_instance.budget = Decimal("5000")
        campaign_instance.start_date = date.today()
        campaign_instance.end_date = date.today() + timedelta(days=30)
        campaign_instance.target_audience = {"segments": ["tech"]}
        campaign_instance.channels = ["paid_search"]
        result = validate_transition(campaign_instance, Campaign.Stage.BRIEF)
        assert result["valid"] is True

    def test_invalid_transition_planning_to_launch(self, campaign_instance):
        result = validate_transition(campaign_instance, Campaign.Stage.LAUNCH)
        assert result["valid"] is False

    def test_get_available_stages(self, campaign_instance):
        stages = get_available_stages(campaign_instance)
        assert len(stages) == 1
        assert stages[0]["stage"] == Campaign.Stage.BRIEF


@pytest.mark.django_db
class TestBudgetService:
    """Tests for budget service."""

    def test_calculate_even_pacing(self, campaign_instance):
        campaign_instance.budget = Decimal("1000")
        campaign_instance.start_date = date.today() - timedelta(days=5)
        campaign_instance.end_date = date.today() + timedelta(days=5)
        campaign_instance.current_spend = Decimal("200")
        campaign_instance.pacing_type = Campaign.PacingType.EVEN
        result = calculate_pacing(campaign_instance)
        assert result["daily_budget"] == 80.0  # 800 / 10
        assert result["pacing_type"] == "even"


class TestABTestingService:
    """Tests for A/B testing service."""

    def test_calculate_sample_size_basic(self):
        result = calculate_sample_size(
            baseline_rate=0.05,
            minimum_detectable_effect=0.20,
            significance=0.05,
            power=0.80,
        )
        assert result["sample_size_per_variant"] > 0
        assert result["total_sample_size"] > 0


class TestChannelsService:
    """Tests for channels service."""

    def test_build_dependency_graph_no_deps(self):
        """Test with mock channel-like objects."""
        pass  # Requires DB channels

    def test_has_cycle_empty(self):
        assert has_cycle({}) is False

    def test_topological_sort_empty(self):
        assert topological_sort({}) == []

    def test_get_channel_recommendations(self):
        result = get_channel_recommendations("conversion")
        assert len(result) == 8
        assert result[0]["score"] >= result[-1]["score"]
