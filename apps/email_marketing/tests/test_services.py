"""Tests for email_marketing services — templates, campaigns, automation."""

from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.email_marketing.models import EmailCampaign, EmailTemplate
from apps.email_marketing.services import automation as automation_service
from apps.email_marketing.services import campaigns as campaign_service
from apps.email_marketing.services import templates as template_service


@pytest.fixture
def tenant_id() -> str:
    return "test-tenant-email"


@pytest.fixture
def create_template(tenant_id, db):
    def _create(**kwargs):
        defaults = {
            "tenant_id": tenant_id,
            "name": f"Template {uuid.uuid4().hex[:8]}",
            "category": EmailTemplate.Category.NEWSLETTER,
            "html": "<html><body>Hello</body></html>",
            "json_design": {"blocks": []},
            "brand_kit": {"primary_color": "#000"},
            "preheader_text": "Test preheader",
            "compatibility_score": Decimal("95.00"),
            "compatibility_results": {"gmail": "ok"},
            "plain_text": "Hello",
        }
        defaults.update(kwargs)
        return EmailTemplate.objects.create(**defaults)

    return _create


@pytest.fixture
def create_campaign(tenant_id, create_template, db):
    def _create(**kwargs):
        template = kwargs.pop("template", None) or create_template()
        defaults = {
            "tenant_id": tenant_id,
            "name": f"Campaign {uuid.uuid4().hex[:8]}",
            "subject_line": "Test Subject",
            "preview_text": "Preview text",
            "from_name": "Test Sender",
            "from_email": "test@example.com",
            "reply_to": "reply@example.com",
            "template": template,
            "status": EmailCampaign.Status.DRAFT,
            "total_recipients": 1000,
        }
        defaults.update(kwargs)
        return EmailCampaign.objects.create(**defaults)

    return _create


# ── Template Service Tests ────────────────────────────────────────


class TestTemplateService:
    def test_list_templates_returns_results(self, create_template):
        t1 = create_template(name="Welcome Email")
        t2 = create_template(name="Newsletter")
        result = template_service.list_templates("test-tenant-email")
        assert result["total"] >= 2
        ids = {t.id for t in result["results"]}
        assert t1.id in ids
        assert t2.id in ids

    def test_list_templates_category_filter(self, create_template):
        create_template(name="Promo", category=EmailTemplate.Category.PROMOTIONAL)
        create_template(name="Welcome", category=EmailTemplate.Category.WELCOME)
        result = template_service.list_templates(
            "test-tenant-email", category=EmailTemplate.Category.PROMOTIONAL
        )
        assert result["total"] == 1
        assert result["results"][0].category == EmailTemplate.Category.PROMOTIONAL

    def test_get_template(self, create_template):
        t = create_template(name="My Template")
        result = template_service.get_template(t.id, "test-tenant-email")
        assert result is not None
        assert result.name == "My Template"

    def test_get_template_not_found(self, tenant_id):
        result = template_service.get_template(99999, tenant_id)
        assert result is None

    def test_create_template(self, tenant_id, db):
        template = template_service.create_template(
            tenant_id=tenant_id,
            name="New Template",
            category=EmailTemplate.Category.NEWSLETTER,
            html="<html><body>New</body></html>",
        )
        assert template is not None
        assert template.name == "New Template"
        assert EmailTemplate.objects.filter(id=template.id).exists()

    def test_duplicate_template(self, create_template, tenant_id):
        t = create_template(name="Original")
        dup = template_service.duplicate_template(t.id, tenant_id=tenant_id)
        assert dup is not None
        assert dup.id != t.id
        assert "Copy" in dup.name

    def test_get_template_compatibility(self, create_template):
        t = create_template(compatibility_score=Decimal("88.50"))
        result = template_service.get_template_compatibility(t.id)
        assert result is not None
        assert result["score"] == Decimal("88.50")

    def test_generate_plain_text(self, create_template):
        t = create_template(html="<html><body><p>Hello World</p></body></html>", plain_text="")
        text = template_service.generate_plain_text(t)
        assert "Hello World" in text

    def test_list_templates_empty_tenant(self, tenant_id):
        result = template_service.list_templates(tenant_id + "-none")
        assert result["total"] == 0
        assert result["results"] == []


# ── Campaign Service Tests ────────────────────────────────────────


class TestCampaignService:
    def test_list_campaigns(self, create_campaign):
        c1 = create_campaign(name="Summer Sale")
        c2 = create_campaign(name="Winter Promo")
        result = campaign_service.list_campaigns("test-tenant-email")
        assert result["total"] >= 2
        ids = {c.id for c in result["results"]}
        assert c1.id in ids
        assert c2.id in ids

    def test_list_campaigns_status_filter(self, create_campaign):
        create_campaign(name="Draft Camp", status=EmailCampaign.Status.DRAFT)
        create_campaign(name="Sent Camp", status=EmailCampaign.Status.SENT)
        result = campaign_service.list_campaigns(
            "test-tenant-email", status=EmailCampaign.Status.DRAFT
        )
        assert result["total"] == 1
        assert result["results"][0].status == EmailCampaign.Status.DRAFT

    def test_get_campaign(self, create_campaign):
        c = create_campaign(name="Test Campaign")
        result = campaign_service.get_campaign(c.id, "test-tenant-email")
        assert result is not None
        assert result.name == "Test Campaign"

    def test_get_campaign_not_found(self, tenant_id):
        result = campaign_service.get_campaign(99999, tenant_id)
        assert result is None

    def test_create_campaign(self, tenant_id, create_template):
        t = create_template()
        campaign = campaign_service.create_campaign(
            tenant_id=tenant_id,
            name="New Campaign",
            subject_line="Subject",
            template_id=t.id,
        )
        assert campaign is not None
        assert campaign.name == "New Campaign"
        assert campaign.status == EmailCampaign.Status.DRAFT
        assert EmailCampaign.objects.filter(id=campaign.id).exists()

    def test_schedule_campaign(self, create_campaign):
        c = create_campaign(name="To Schedule", status=EmailCampaign.Status.DRAFT)
        scheduled_at = timezone.now() + timedelta(hours=2)
        updated = campaign_service.schedule_campaign(c.id, scheduled_at=scheduled_at)
        assert updated.status == EmailCampaign.Status.SCHEDULED
        assert updated.scheduled_at is not None

    def test_pause_and_resume_campaign(self, create_campaign):
        c = create_campaign(name="Pause Test", status=EmailCampaign.Status.SENDING)
        paused = campaign_service.pause_campaign(c.id)
        assert paused.status == EmailCampaign.Status.PAUSED
        resumed = campaign_service.resume_campaign(paused.id)
        assert resumed.status == EmailCampaign.Status.SENDING

    def test_duplicate_campaign(self, create_campaign):
        c = create_campaign(name="Original Campaign")
        dup = campaign_service.duplicate_campaign(c.id, "test-tenant-email")
        assert dup is not None
        assert dup.id != c.id
        assert "Copy" in dup.name

    def test_get_campaign_stats(self, create_campaign):
        c = create_campaign(
            name="Stats Camp",
            total_recipients=1000,
            delivered=950,
            unique_opens=475,
            unique_clicks=95,
            bounces=50,
        )
        stats = campaign_service.get_campaign_stats(c.id)
        assert stats["total_recipients"] == 1000
        assert stats["delivered"] == 950
        assert stats["open_rate"] == 50.0

    def test_list_campaigns_empty_tenant(self, tenant_id):
        result = campaign_service.list_campaigns(tenant_id + "-none")
        assert result["total"] == 0
        assert result["results"] == []


# ── Automation Service Tests ──────────────────────────────────────


class TestAutomationService:
    def test_create_sequence(self, tenant_id, db):
        seq = automation_service.create_sequence(
            tenant_id=tenant_id,
            name="Welcome Sequence",
            description="Welcome new subscribers",
        )
        assert seq is not None
        assert seq.name == "Welcome Sequence"
        assert seq.status == "draft"

    def test_list_sequences(self, tenant_id, db):
        automation_service.create_sequence(tenant_id=tenant_id, name="Seq One")
        automation_service.create_sequence(tenant_id=tenant_id, name="Seq Two")
        result = automation_service.list_sequences(tenant_id)
        assert result["total"] >= 2

    def test_add_sequence_step(self, tenant_id, db):
        seq = automation_service.create_sequence(tenant_id=tenant_id, name="Step Test")
        step = automation_service.add_sequence_step(
            sequence_id=seq.id,
            tenant_id=tenant_id,
            step_number=1,
            delay_hours=0,
            template_name="welcome",
        )
        assert step is not None
        assert step["step_number"] == 1

    def test_list_sequences_empty(self, tenant_id):
        result = automation_service.list_sequences(tenant_id + "-none")
        assert result["total"] == 0
        assert result["results"] == []

    def test_activate_sequence(self, tenant_id, db):
        seq = automation_service.create_sequence(tenant_id=tenant_id, name="Activate Test")
        updated = automation_service.activate_sequence(seq.id, tenant_id)
        assert updated is not None
        assert updated.status == "active"
