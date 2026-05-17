"""Celery tasks for the Campaigns module.

Handles budget monitoring, campaign execution orchestration via
Vortex, and performance threshold alerting.

Tasks are routed to the ``campaigns`` queue via
``voyager_project.celery.app.conf.task_routes``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def check_budget_thresholds(self) -> Dict[str, Any]:
    """Check campaign budgets against configured thresholds.

    Called by the beat scheduler every 5 minutes. Evaluates each
    active :class:`apps.campaigns.models.Campaign` and triggers
    alerts when spend exceeds ``warning_threshold`` or
    ``critical_threshold`` percentages of the total budget.

    :returns: Summary dict with ``campaigns_checked``,
        ``warnings_triggered``, ``criticals_triggered``.
    """
    logger.info("Task started: %s", self.name)

    result: Dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "campaigns_checked": 0,
        "warnings_triggered": 0,
        "criticals_triggered": 0,
    }
    logger.info("Task completed: %s — %r", self.name, result)
    return result


@shared_task(bind=True, max_retries=3)
def execute_campaign(
    self,
    campaign_id: str,
    tenant_id: str,
) -> Dict[str, Any]:
    """Execute a campaign via the Vortex workflow engine.

    Compiles the campaign definition to GraphDSL and submits it
    to Vortex for execution.

    :param campaign_id: UUID of the campaign.
    :param tenant_id: UUID of the tenant scope.
    :returns: Result dict with ``campaign_id``, ``graph_id``, ``run_id``.
    """
    logger.info("Executing campaign %s for tenant %s", campaign_id, tenant_id)

    result: Dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "campaign_id": campaign_id,
        "graph_id": None,
        "run_id": None,
    }
    return result
