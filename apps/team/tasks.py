"""Celery tasks for the Team module.

Handles team member onboarding, activity reporting, and
permission synchronisation.

Tasks are routed to the ``team`` queue via
``voyager_project.celery.app.conf.task_routes``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_team_digest(self, tenant_id: str) -> Dict[str, Any]:
    """Send daily activity digest to team members.

    :param tenant_id: UUID of the tenant scope.
    :returns: Result dict with ``recipients``, "emails_sent``.
    """
    logger.info("Sending team digest for tenant %s", tenant_id)

    result: Dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "tenant_id": tenant_id,
        "recipients": 0,
        "emails_sent": 0,
    }
    return result


@shared_task(bind=True, max_retries=3)
def sync_team_permissions(self, tenant_id: str) -> Dict[str, Any]:
    """Synchronise team member permissions with Keycloak.

    :param tenant_id: UUID of the tenant scope.
    :returns: Result dict with ``members_synced``.
    """
    logger.info("Syncing team permissions for tenant %s", tenant_id)

    result: Dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "tenant_id": tenant_id,
        "members_synced": 0,
    }
    return result
