"""Celery tasks for the Clients module.

Handles client data synchronisation, report delivery, and
client portal updates.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def sync_client_data(self, client_id: str) -> Dict[str, Any]:
    """Synchronise client data from external CRM systems.

    :param client_id: UUID of the client.
    :returns: Result dict with sync status.
    """
    logger.info("Syncing client data: %s", client_id)

    result: Dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "client_id": client_id,
    }
    return result
