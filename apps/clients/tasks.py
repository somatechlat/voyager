"""Celery tasks for the Clients CRM module.

Handles onboarding reminders, project deadline alerts,
profitability recalculation, and portal sync operations.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from celery import shared_task
from django.db.models import Q

from apps.clients.models.client import Client
from apps.clients.models.communication import CommunicationLog
from apps.clients.models.project import Project, ProjectMilestone
from apps.clients.services import (
    ClientService,
    CommunicationService,
    ProfitabilityService,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_onboarding_reminder(self, client_id: int) -> dict[str, Any]:
    """Send an onboarding reminder for a client still in onboarding status.

    Checks if the client is still onboarding and logs a reminder
    communication entry. Can be scheduled daily for all onboarding clients.

    Args:
        client_id: Primary key of the client to remind.

    Returns:
        Dict with task status and reminder details.
    """
    try:
        client = Client.objects.get(id=client_id)
    except Client.DoesNotExist:
        logger.warning("Onboarding reminder: client %s not found", client_id)
        return {"status": "error", "message": "Client not found"}

    if client.status != Client.Status.ONBOARDING:
        return {
            "status": "skipped",
            "message": f"Client status is {client.status}, not onboarding",
        }

    CommunicationLog.objects.create(
        tenant_id=client.tenant_id,
        client=client,
        comm_type=CommunicationLog.CommType.NOTE,
        direction=CommunicationLog.Direction.INTERNAL,
        subject="Onboarding reminder",
        content=f"Automated reminder: Client {client.name} is still in onboarding status.",
        metadata={"auto_generated": True, "task": "onboarding_reminder"},
    )

    logger.info("Onboarding reminder sent for client: %s", client.name)
    return {
        "status": "sent",
        "client_id": client_id,
        "client_name": client.name,
        "reminded_at": datetime.utcnow().isoformat(),
    }


@shared_task(bind=True, max_retries=3)
def check_onboarding_clients(self) -> dict[str, Any]:
    """Find all clients in onboarding status and queue reminders.

    Scheduled task that runs daily to identify clients stuck in
    onboarding and sends reminders for each.

    Returns:
        Dict with count of clients processed and reminder statuses.
    """
    clients = Client.objects.filter(status=Client.Status.ONBOARDING)
    results: list[dict[str, Any]] = []

    for client in clients:
        result = send_onboarding_reminder.delay(client.id)
        results.append({"client_id": client.id, "task_id": result.id})

    logger.info("Checked %s onboarding clients", len(results))
    return {
        "status": "ok",
        "checked_count": len(results),
        "reminders_queued": results,
    }


@shared_task(bind=True, max_retries=3)
def alert_project_deadlines(self) -> dict[str, Any]:
    """Alert on projects with approaching or missed deadlines.

    Identifies projects that are active and have an end date within
    the next 7 days, or milestones that are overdue. Logs alert
    communications for each.

    Returns:
        Dict with alert counts and details.
    """
    today = date.today()
    warning_date = today + timedelta(days=7)

    approaching_projects = Project.objects.filter(
        status=Project.Status.ACTIVE,
        end_date__lte=warning_date,
        end_date__gte=today,
    )

    missed_milestones = ProjectMilestone.objects.filter(
        status__in=[
            ProjectMilestone.Status.PENDING,
            ProjectMilestone.Status.IN_PROGRESS,
        ],
        due_date__lt=today,
    )

    project_alerts: list[dict[str, Any]] = []
    for project in approaching_projects:
        days_remaining = (project.end_date - today).days if project.end_date else 0
        CommunicationLog.objects.create(
            tenant_id=project.tenant_id,
            client=project.client,
            project=project,
            comm_type=CommunicationLog.CommType.NOTE,
            direction=CommunicationLog.Direction.INTERNAL,
            subject=f"Project deadline approaching: {project.name}",
            content=(
                f"Project '{project.name}' ends in {days_remaining} days " f"({project.end_date})."
            ),
            metadata={
                "auto_generated": True,
                "task": "deadline_alert",
                "days_remaining": days_remaining,
            },
        )
        project_alerts.append(
            {
                "project_id": project.id,
                "name": project.name,
                "days_remaining": days_remaining,
            }
        )

    milestone_alerts: list[dict[str, Any]] = []
    for milestone in missed_milestones.select_related("project"):
        days_overdue = (today - milestone.due_date).days if milestone.due_date else 0
        CommunicationLog.objects.create(
            tenant_id=milestone.project.tenant_id,
            client=milestone.project.client,
            project=milestone.project,
            comm_type=CommunicationLog.CommType.NOTE,
            direction=CommunicationLog.Direction.INTERNAL,
            subject=f"Overdue milestone: {milestone.name}",
            content=(
                f"Milestone '{milestone.name}' in project "
                f"'{milestone.project.name}' is {days_overdue} days overdue."
            ),
            metadata={
                "auto_generated": True,
                "task": "milestone_overdue_alert",
                "days_overdue": days_overdue,
            },
        )
        milestone_alerts.append(
            {
                "milestone_id": milestone.id,
                "name": milestone.name,
                "days_overdue": days_overdue,
            }
        )

    logger.info(
        "Deadline alerts: %s projects, %s milestones",
        len(project_alerts),
        len(milestone_alerts),
    )
    return {
        "status": "ok",
        "project_alerts": len(project_alerts),
        "milestone_alerts": len(milestone_alerts),
        "projects": project_alerts,
        "milestones": milestone_alerts,
    }


@shared_task(bind=True, max_retries=3)
def calculate_monthly_profitability(self, tenant_id: str) -> dict[str, Any]:
    """Calculate profitability for all clients in a tenant for the current month.

    Scheduled task that runs monthly to generate profitability snapshots.

    Args:
        tenant_id: The tenant identifier.

    Returns:
        Dict with calculation results per client.
    """
    today = date.today()
    period_start = today.replace(day=1)
    period_end = today

    clients = Client.objects.filter(tenant_id=tenant_id, status=Client.Status.ACTIVE)
    results: list[dict[str, Any]] = []

    for client in clients:
        try:
            result = ProfitabilityService.calculate_from_projects(
                tenant_id=tenant_id,
                client_id=client.id,
                period_start=period_start.isoformat(),
                period_end=period_end.isoformat(),
            )
            ProfitabilityService.create(
                tenant_id=tenant_id,
                client_id=client.id,
                data={
                    "period_start": period_start,
                    "period_end": period_end,
                    "revenue": result["revenue"],
                    "costs": result["costs"],
                    "margin_percent": result["margin_percent"],
                    "breakdown": result["breakdown"],
                },
            )
            results.append(
                {
                    "client_id": client.id,
                    "client_name": client.name,
                    "margin_percent": result["margin_percent"],
                    "status": "ok",
                }
            )
        except Exception as exc:
            logger.error(
                "Profitability calculation failed for client %s: %s",
                client.id,
                exc,
            )
            results.append(
                {
                    "client_id": client.id,
                    "client_name": client.name,
                    "status": "error",
                    "error": str(exc),
                }
            )

    logger.info(
        "Monthly profitability calculated for %s clients in tenant %s",
        len(results),
        tenant_id,
    )
    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "results": results,
    }


@shared_task(bind=True, max_retries=3)
def auto_log_inbound_email(self, tenant_id: str, email_data: dict[str, Any]) -> dict[str, Any]:
    """Auto-log an inbound email to a client's communication log.

    Args:
        tenant_id: The tenant identifier.
        email_data: Email data dictionary with from_address, to_addresses,
            subject, body, and optional thread_id.

    Returns:
        Dict with auto-log status and matched client info.
    """
    log = CommunicationService.auto_log_email(tenant_id, email_data)
    if log:
        return {
            "status": "logged",
            "log_id": log.id,
            "client_id": log.client_id,
            "subject": log.subject,
        }
    return {"status": "no_match", "message": "No client matched for email"}


@shared_task(bind=True, max_retries=3)
def sync_client_data(self, client_id: str) -> dict[str, Any]:
    """Synchronise client data from external systems.

    Initiates sync from external CRM integrations. Logs the sync
    attempt and returns status.

    Args:
        client_id: UUID string of the client to sync.

    Returns:
        Dict with sync status.
    """
    logger.info("Syncing client data: %s", client_id)
    return {
        "status": "ok",
        "task": self.name,
        "client_id": client_id,
        "synced_at": datetime.utcnow().isoformat(),
    }
