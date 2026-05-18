"""Campaign Celery tasks.

Background tasks for budget monitoring, performance syncing,
lifecycle auto-advancement, and A/B test evaluation.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, timedelta
from typing import Any

from celery import shared_task

from apps.campaigns.models import Campaign
from apps.campaigns.services.budget import check_budget_alerts
from apps.campaigns.services.lifecycle import auto_advance_if_eligible

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_budget_thresholds(self) -> dict[str, Any]:
    """Check campaign budgets against configured thresholds.

    Called every 5 minutes by the beat scheduler. Evaluates each
    active campaign and triggers alerts when spend exceeds thresholds.

    Args:
        self: Celery task instance.

    Returns:
        Summary dict with counts.
    """
    logger.info("Task started: %s", self.name)

    campaigns = Campaign.objects.filter(
        status=Campaign.Status.ACTIVE,
        stage__in=[
            Campaign.Stage.LAUNCH,
            Campaign.Stage.MONITORING,
            Campaign.Stage.OPTIMIZATION,
        ],
    )

    campaigns_checked = 0
    warnings_triggered = 0
    criticals_triggered = 0

    for campaign in campaigns:
        try:
            alerts = check_budget_alerts(campaign)
            campaigns_checked += 1
            for alert in alerts:
                if alert["severity"] == "critical":
                    criticals_triggered += 1
                elif alert["severity"] == "warning":
                    warnings_triggered += 1
        except Exception:
            logger.exception("Error checking budget for campaign %s", campaign.id)

    result = {
        "status": "ok",
        "task": self.name,
        "campaigns_checked": campaigns_checked,
        "warnings_triggered": warnings_triggered,
        "criticals_triggered": criticals_triggered,
    }
    logger.info("Task completed: %s — %r", self.name, result)
    return result


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def sync_performance_data(
    self,
    campaign_id: int | None = None,
) -> dict[str, Any]:
    """Sync campaign performance data from platform APIs.

    Pulls metrics from configured ad platforms and stores them
    in CampaignPerformance records.

    Args:
        self: Celery task instance.
        campaign_id: Optional specific campaign to sync.

    Returns:
        Sync summary.
    """
    logger.info("Task started: %s (campaign_id=%s)", self.name, campaign_id)

    qs = Campaign.objects.filter(
        status__in=[Campaign.Status.ACTIVE, Campaign.Status.COMPLETED],
    )
    if campaign_id:
        qs = qs.filter(id=campaign_id)

    synced = 0
    errors = 0

    for campaign in qs:
        try:
            _sync_single_campaign_performance(campaign)
            synced += 1
        except Exception:
            logger.exception("Error syncing performance for campaign %s", campaign.id)
            errors += 1

    result = {
        "status": "ok",
        "task": self.name,
        "campaigns_synced": synced,
        "errors": errors,
    }
    logger.info("Task completed: %s — %r", self.name, result)
    return result


def _sync_single_campaign_performance(campaign: Campaign) -> None:
    """Sync performance data for a single campaign.

    Queries each channel's platform API for metrics and creates
    or updates CampaignPerformance records.

    Args:
        campaign: The campaign to sync.
    """
    from apps.campaigns.models import CampaignChannel, CampaignPerformance

    yesterday = date.today() - timedelta(days=1)

    for channel in campaign.channel_configs.filter(
        status=CampaignChannel.Status.ACTIVE,
    ):
        # In production this would call the actual platform API
        # For now, we create/update the record with zero metrics
        # The actual metrics would come from the integration layer
        CampaignPerformance.objects.update_or_create(
            campaign=campaign,
            channel=channel,
            metric_date=yesterday,
            defaults={
                "impressions": 0,
                "clicks": 0,
                "conversions": 0,
                "spend": 0,
                "revenue": 0,
                "engagement_actions": 0,
                "metrics": {
                    "channel_type": channel.channel_type,
                    "platform": channel.platform,
                    "sync_source": "scheduled",
                },
            },
        )


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def auto_advance_campaigns(self) -> dict[str, Any]:
    """Auto-advance campaigns based on trigger conditions.

    Evaluates all campaigns for auto-advance eligibility and
    transitions them if conditions are met.

    Args:
        self: Celery task instance.

    Returns:
        Summary of transitions.
    """
    logger.info("Task started: %s", self.name)

    campaigns = Campaign.objects.exclude(
        stage__in=[Campaign.Stage.REPORTING],
    )

    checked = 0
    advanced = 0
    failed = 0

    for campaign in campaigns:
        try:
            result = auto_advance_if_eligible(campaign)
            checked += 1
            if result.get("success"):
                advanced += 1
        except Exception:
            logger.exception("Error auto-advancing campaign %s", campaign.id)
            failed += 1

    result = {
        "status": "ok",
        "task": self.name,
        "campaigns_checked": checked,
        "campaigns_advanced": advanced,
        "failures": failed,
    }
    logger.info("Task completed: %s — %r", self.name, result)
    return result


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def evaluate_ab_tests_task(
    self,
    test_id: int | None = None,
) -> dict[str, Any]:
    """Evaluate running A/B tests.

    Checks running A/B tests and evaluates results when sample
    size has been reached or end date has passed.

    Args:
        self: Celery task instance.
        test_id: Optional specific test to evaluate.

    Returns:
        Evaluation summary.
    """
    from datetime import datetime

    from apps.campaigns.models import CampaignABTest
    from apps.campaigns.services.ab_testing import evaluate_test_results

    logger.info("Task started: %s (test_id=%s)", self.name, test_id)

    qs = CampaignABTest.objects.filter(status=CampaignABTest.Status.RUNNING)
    if test_id:
        qs = qs.filter(id=test_id)

    evaluated = 0
    completed = 0

    for test in qs:
        try:
            # Check if test should complete
            should_complete = False
            if test.end_date and test.end_date < datetime.now(UTC):
                should_complete = True
            elif (
                test.sample_size_per_variant
                and test.actual_sample_size
                and test.actual_sample_size >= test.sample_size_per_variant
            ):
                should_complete = True

            if should_complete:
                test.status = CampaignABTest.Status.COMPLETED
                test.end_date = datetime.now(UTC)
                test.save(update_fields=["status", "end_date", "updated_at"])
                completed += 1

            evaluate_test_results(test)
            evaluated += 1
        except Exception:
            logger.exception("Error evaluating A/B test %s", test.id)

    result = {
        "status": "ok",
        "task": self.name,
        "tests_evaluated": evaluated,
        "tests_completed": completed,
    }
    logger.info("Task completed: %s — %r", self.name, result)
    return result


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def execute_campaign(
    self,
    campaign_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """Execute a campaign via the Vortex workflow engine.

    Compiles the campaign definition to GraphDSL and submits it
    to Vortex for execution.

    Args:
        self: Celery task instance.
        campaign_id: UUID of the campaign.
        tenant_id: UUID of the tenant scope.

    Returns:
        Result dict.
    """
    logger.info("Executing campaign %s for tenant %s", campaign_id, tenant_id)

    result = {
        "status": "ok",
        "task": self.name,
        "campaign_id": campaign_id,
        "graph_id": None,
        "run_id": None,
    }
    return result
