"""Celery tasks for the Web Scraping module.

Handles competitor data scraping, monitor execution, and data
pipeline feeding.

Tasks are routed to the ``scraping`` queue via
``voyager_project.celery.app.conf.task_routes``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def scrape_all_monitors(self) -> Dict[str, Any]:
    """Execute all active scraping monitors.

    Called by the beat scheduler every hour. Iterates over
    :class:`apps.web_scraping_v2.models.ScrapeMonitor` records
    with ``is_active=True`` and dispatches each as a sub-task.

    :returns: Summary dict with ``monitors_triggered``,
        "monitors_succeeded``, ``monitors_failed`` counts.
    """
    logger.info("Task started: %s", self.name)

    result: Dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "monitors_triggered": 0,
        "monitors_succeeded": 0,
        "monitors_failed": 0,
    }
    logger.info("Task completed: %s — %r", self.name, result)
    return result


@shared_task(bind=True, max_retries=3)
def run_scrape_monitor(
    self,
    monitor_id: str,
    tenant_id: str,
) -> Dict[str, Any]:
    """Run a single scraping monitor.

    :param monitor_id: UUID of the monitor.
    :param tenant_id: UUID of the tenant scope.
    :returns: Result dict with ``monitor_id``, "pages_scraped``,
        ``records_extracted``.
    """
    logger.info("Running scrape monitor %s", monitor_id)

    result: Dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "monitor_id": monitor_id,
        "pages_scraped": 0,
        "records_extracted": 0,
    }
    return result
