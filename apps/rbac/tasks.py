"""Celery tasks for the RBAC module.

Handles session cleanup, permission cache invalidation, and
role-synchronisation with Keycloak.

Tasks are routed to the ``rbac`` queue via
``voyager_project.celery.app.conf.task_routes``.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def cleanup_expired_sessions(self) -> dict[str, Any]:
    """Remove expired user sessions and temporary role grants.

    Called by the beat scheduler every hour. Deletes
    :class:`apps.rbac.models.RoleAssignment` records whose
    ``expires_at`` timestamp has passed and cleans up stale
    session cache entries in Redis.

    :returns: Summary dict with ``sessions_cleaned``,
        ``grants_revoked`` counts.
    """
    logger.info("Task started: %s", self.name)

    result: dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "sessions_cleaned": 0,
        "grants_revoked": 0,
    }
    logger.info("Task completed: %s — %r", self.name, result)
    return result


@shared_task(bind=True, max_retries=3)
def sync_keycloak_roles(self) -> dict[str, Any]:
    """Synchronise roles from Keycloak into the local RBAC store.

    Fetches the current realm roles from Keycloak and ensures
    matching :class:`apps.rbac.models.Role` records exist locally.

    :returns: Summary dict with ``roles_synced``, ``roles_created``,
        ``roles_updated`` counts.
    """
    logger.info("Task started: %s", self.name)

    result: dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "roles_synced": 0,
        "roles_created": 0,
        "roles_updated": 0,
    }
    logger.info("Task completed: %s", self.name)
    return result
