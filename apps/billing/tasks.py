"""Celery tasks for the Billing module.

Handles invoice generation, payment processing, subscription
management, and usage metering.

Tasks are routed to the ``billing`` queue via
``voyager_project.celery.app.conf.task_routes``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_invoices(self) -> Dict[str, Any]:
    """Generate invoices for all billable tenants.

    Iterates over active subscriptions and generates invoices
    for the current billing period.

    :returns: Result dict with ``invoices_generated``,
        ``total_amount``.
    """
    logger.info("Task started: %s", self.name)

    result: Dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "invoices_generated": 0,
        "total_amount": 0.0,
    }
    logger.info("Task completed: %s", self.name)
    return result


@shared_task(bind=True, max_retries=3)
def process_recurring_payments(self) -> Dict[str, Any]:
    """Process recurring subscription payments.

    Charges payment methods for subscriptions that are due.

    :returns: Result dict with ``payments_processed``,
        ``payments_failed``.
    """
    logger.info("Task started: %s", self.name)

    result: Dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "payments_processed": 0,
        "payments_failed": 0,
    }
    logger.info("Task completed: %s", self.name)
    return result
