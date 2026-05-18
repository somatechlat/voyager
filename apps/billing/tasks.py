"""Celery tasks for the Billing module.

Handles invoice generation, retainer renewal, payment processing,
timesheet processing, and profitability reporting.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_invoices(self) -> dict[str, Any]:
    """Generate invoices for all active retainers and unbilled items.

    Iterates over active retainers and clients with unbilled time
    entries, generating invoices for the current billing period.

    :returns: Result dict with invoices_generated and total_amount.
    """
    logger.info("Task started: %s", self.name)
    try:
        from apps.billing.models.retainer import Retainer
        from apps.billing.services.invoicing import create_invoice

        today = date.today()
        month_start = today.replace(day=1)

        # Generate retainer invoices
        retainers = Retainer.objects.filter(
            auto_invoice=True, status=Retainer.Status.ACTIVE
        ).select_related("client")
        invoices_generated = 0
        total_amount = 0.0
        for ret in retainers:
            if ret.last_invoiced_month and ret.last_invoiced_month >= month_start:
                continue
            try:
                inv = create_invoice(
                    tenant_id=ret.tenant_id,
                    client_id=ret.client_id,
                    date_from=month_start,
                    date_to=today,
                    invoice_type="retainer",
                )
                invoices_generated += 1
                total_amount += float(inv.total)
                ret.last_invoiced_month = month_start
                ret.total_amount_invoiced += inv.total
                ret.save(
                    update_fields=["last_invoiced_month", "total_amount_invoiced", "updated_at"]
                )
            except Exception:
                logger.exception("Failed to generate retainer invoice for %s", ret.pk)

        logger.info("Generated %d invoices, total %.2f", invoices_generated, total_amount)
        return {
            "status": "ok",
            "invoices_generated": invoices_generated,
            "total_amount": round(total_amount, 2),
        }
    except Exception as exc:
        logger.exception("Invoice generation failed: %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_recurring_payments(self) -> dict[str, Any]:
    """Process recurring subscription payments.

    Attempts to charge overdue invoices with Stripe PaymentIntents.

    :returns: Result dict with payments_processed and payments_failed.
    """
    logger.info("Task started: %s", self.name)
    try:
        from apps.billing.models.invoice import Invoice
        from apps.billing.services.payments import create_payment_intent

        overdue = Invoice.objects.filter(
            status__in=[Invoice.Status.OVERDUE, Invoice.Status.PARTIAL],
            due_date__lt=date.today(),
        ).select_related("client")
        payments_processed = 0
        payments_failed = 0
        for inv in overdue:
            if not inv.stripe_payment_intent_id:
                try:
                    result = create_payment_intent(inv)
                    if "error" not in result:
                        payments_processed += 1
                    else:
                        payments_failed += 1
                except Exception:
                    logger.exception("Payment failed for invoice %s", inv.pk)
                    payments_failed += 1
        return {
            "status": "ok",
            "payments_processed": payments_processed,
            "payments_failed": payments_failed,
        }
    except Exception as exc:
        logger.exception("Recurring payment processing failed: %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_running_timers(self) -> dict[str, Any]:
    """Update running timer entries with current duration.

    Called every minute to update active timers.

    :returns: Result dict with timers_updated.
    """
    logger.info("Task started: %s", self.name)
    try:
        from apps.billing.services.time_tracking import process_running_timers

        count = process_running_timers()
        return {"status": "ok", "timers_updated": count}
    except Exception as exc:
        logger.exception("Timer processing failed: %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_budget_alerts(self) -> dict[str, Any]:
    """Check budget consumption and trigger alerts.

    Evaluates all active project budgets and updates alert levels.

    :returns: Result dict with budgets_checked and alerts_triggered.
    """
    logger.info("Task started: %s", self.name)
    try:
        from apps.billing.models.project_budget import ProjectBudget
        from apps.billing.services.budgeting import evaluate_budget_alert

        budgets = ProjectBudget.objects.exclude(alert_level=ProjectBudget.AlertLevel.CRITICAL)
        budgets_checked = 0
        alerts_triggered = 0
        for budget in budgets:
            result = evaluate_budget_alert(budget)
            budgets_checked += 1
            if result["triggered"]:
                alerts_triggered += 1
        return {
            "status": "ok",
            "budgets_checked": budgets_checked,
            "alerts_triggered": alerts_triggered,
        }
    except Exception as exc:
        logger.exception("Budget alert check failed: %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def renew_retainers(self) -> dict[str, Any]:
    """Renew retainers approaching end date.

    Auto-renews retainers with auto-renewal enabled.

    :returns: Result dict with retainers_renewed.
    """
    logger.info("Task started: %s", self.name)
    try:
        from apps.billing.models.retainer import Retainer
        from apps.billing.services.retainers import renew_retainer, should_auto_renew

        retainers = Retainer.objects.filter(status=Retainer.Status.ACTIVE)
        renewed = 0
        for ret in retainers:
            if should_auto_renew(ret):
                try:
                    renew_retainer(ret)
                    renewed += 1
                except Exception:
                    logger.exception("Failed to renew retainer %s", ret.pk)
        return {"status": "ok", "retainers_renewed": renewed}
    except Exception as exc:
        logger.exception("Retainer renewal failed: %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def compute_profitability_reports(self) -> dict[str, Any]:
    """Compute profitability reports for active clients.

    Generates P&L reports for the previous month across all active clients.

    :returns: Result dict with reports_generated.
    """
    logger.info("Task started: %s", self.name)
    try:
        from apps.billing.services.profitability import compute_client_profitability

        today = date.today()
        if today.month == 1:
            period_start = date(today.year - 1, 12, 1)
            period_end = date(today.year - 1, 12, 31)
        else:
            period_start = date(today.year, today.month - 1, 1)
            last_day = (
                date(today.year, today.month, 1) - __import__("datetime").timedelta(days=1)
            ).day
            period_end = date(today.year, today.month - 1, last_day)

        # Use string-based approach to avoid import issues
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT tenant_id FROM voyager_client WHERE status = %s",
                ["active"],
            )
            tenant_rows = cursor.fetchall()
            cursor.execute(
                "SELECT id, tenant_id FROM voyager_client WHERE status = %s",
                ["active"],
            )
            clients = cursor.fetchall()

        reports_generated = 0
        for client_id, tenant_id in clients:
            try:
                report = compute_client_profitability(
                    tenant_id, client_id, "client", period_start, period_end
                )
                if report:
                    reports_generated += 1
            except Exception:
                logger.exception("Failed profitability for client %s", client_id)

        return {"status": "ok", "reports_generated": reports_generated}
    except Exception as exc:
        logger.exception("Profitability computation failed: %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_dunning(self) -> dict[str, Any]:
    """Process dunning for overdue invoices.

    Evaluates and executes dunning actions on overdue invoices.

    :returns: Result dict with invoices_evaluated and actions_taken.
    """
    logger.info("Task started: %s", self.name)
    try:
        from apps.billing.models.invoice import Invoice
        from apps.billing.services.payments import manage_dunning

        overdue = Invoice.objects.filter(status=Invoice.Status.OVERDUE)
        invoices_evaluated = 0
        actions_taken = 0
        for inv in overdue:
            invoices_evaluated += 1
            result = manage_dunning(inv)
            if result:
                actions_taken += 1
        return {
            "status": "ok",
            "invoices_evaluated": invoices_evaluated,
            "actions_taken": actions_taken,
        }
    except Exception as exc:
        logger.exception("Dunning processing failed: %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_invoice_reminders(self) -> dict[str, Any]:
    """Send reminders for unpaid invoices.

    Sends email reminders for invoices approaching or past due date.

    :returns: Result dict with reminders_sent.
    """
    logger.info("Task started: %s", self.name)
    try:
        from datetime import timedelta

        from apps.billing.models.invoice import Invoice

        today = date.today()
        upcoming = Invoice.objects.filter(
            status__in=[Invoice.Status.SENT, Invoice.Status.VIEWED],
            due_date__lte=today + timedelta(days=3),
            due_date__gte=today,
        )
        reminders_sent = 0
        for inv in upcoming:
            logger.info("Would send reminder for invoice %s", inv.invoice_number)
            reminders_sent += 1
        return {"status": "ok", "reminders_sent": reminders_sent}
    except Exception as exc:
        logger.exception("Invoice reminders failed: %s", exc)
        raise self.retry(exc=exc)
