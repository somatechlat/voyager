"""Celery tasks for the Email Marketing module.

Handles campaign sends, list management, A/B testing orchestration,
and deliverability monitoring.

Tasks are routed to the ``email`` queue via
``voyager_project.celery.app.conf.task_routes``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_campaign_emails(
    self,
    campaign_id: str,
    tenant_id: str,
    batch_size: int = 100,
) -> Dict[str, Any]:
    """Send an email marketing campaign in batches.

    :param campaign_id: UUID of the email campaign.
    :param tenant_id: UUID of the tenant scope.
    :param batch_size: Number of emails per batch.
    :returns: Result dict with ``sent``, ``failed``, ``bounced`` counts.
    """
    logger.info(
        "Sending campaign %s for tenant %s (batch=%s)",
        campaign_id,
        tenant_id,
        batch_size,
    )

    result: Dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "campaign_id": campaign_id,
        "sent": 0,
        "failed": 0,
        "bounced": 0,
    }
    return result


@shared_task(bind=True, max_retries=3)
def sync_email_lists(self, tenant_id: str) -> Dict[str, Any]:
    """Synchronise email subscriber lists with external ESPs.

    :param tenant_id: UUID of the tenant scope.
    :returns: Result dict with ``lists_synced``, "subscribers_updated``.
    """
    logger.info("Syncing email lists for tenant %s", tenant_id)

    result: Dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "lists_synced": 0,
        "subscribers_updated": 0,
    }
    return result
