"""Celery tasks for the Workflows v2 module.

Handles workflow execution triggers, state transitions,
scheduled trigger evaluation, approval timeout monitoring,
and integration with the Vortex workflow engine.

Tasks are routed to the ``workflows`` queue via
``voyager_project.celery.app.conf.task_routes``.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def execute_workflow(
    self,
    workflow_id: int,
    tenant_id: str,
    trigger_data: dict[str, Any],
    trigger_type: str = "manual",
    user_id: str | None = None,
) -> dict[str, Any]:
    """Execute a workflow definition via Vortex.

    Creates an execution record, compiles the workflow to GraphDSL,
    submits it to Vortex, and tracks the execution lifecycle.

    :param workflow_id: ID of the workflow to execute.
    :param tenant_id: Tenant scope.
    :param trigger_data: Data that triggered the workflow.
    :param trigger_type: Type of trigger (manual, scheduled, webhook).
    :param user_id: User who initiated the execution.
    :returns: Result dict with execution status and IDs.
    """
    logger.info(
        "Executing workflow %s for tenant %s (trigger=%s)",
        workflow_id,
        tenant_id,
        trigger_type,
    )

    try:
        from apps.workflows_v2.models.workflow import Workflow
        from apps.workflows_v2.services.execution import start_execution

        workflow = Workflow.objects.get(id=workflow_id, tenant_id=tenant_id)
        execution = start_execution(
            workflow=workflow,
            trigger_type=trigger_type,
            trigger_data=trigger_data,
            user_id=user_id,
        )

        result: dict[str, Any] = {
            "status": "started",
            "workflow_id": workflow_id,
            "execution_id": execution.id,
            "version": workflow.version,
        }
        logger.info("Execution %s started for workflow %s", execution.id, workflow_id)
        return result

    except Workflow.DoesNotExist:
        logger.error("Workflow %s not found for tenant %s", workflow_id, tenant_id)
        return {"status": "error", "workflow_id": workflow_id, "error": "Workflow not found"}
    except Exception as exc:
        logger.error("Execution error for workflow %s: %s", workflow_id, exc)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60)
        return {
            "status": "failed",
            "workflow_id": workflow_id,
            "error": str(exc),
        }


@shared_task(bind=True, max_retries=3)
def cleanup_stale_workflow_runs(self) -> dict[str, Any]:
    """Clean up workflow runs stuck in non-terminal states.

    Finds executions that have been in ``running`` or ``pending``
    longer than the configured timeout and marks them as ``failed``.

    :returns: Result dict with count of cleaned runs.
    """
    logger.info("Task started: %s", self.name)

    from apps.workflows_v2.models.execution import WorkflowExecution

    timeout_hours = 24
    cutoff = timezone.now() - timezone.timedelta(hours=timeout_hours)

    stale = WorkflowExecution.objects.filter(
        status__in=[WorkflowExecution.STATUS_RUNNING, WorkflowExecution.STATUS_PENDING],
        started_at__lt=cutoff,
    )
    count = stale.count()

    if count > 0:
        stale.update(
            status=WorkflowExecution.STATUS_FAILED,
            error="Execution timed out — exceeded maximum runtime",
            completed_at=timezone.now(),
        )
        logger.info("Marked %s stale executions as failed (cutoff: %s)", count, cutoff)

    result: dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "runs_cleaned": count,
        "cutoff": cutoff.isoformat(),
    }
    logger.info("Task completed: %s (cleaned %s runs)", self.name, count)
    return result


@shared_task(bind=True, max_retries=3)
def evaluate_scheduled_triggers(self) -> dict[str, Any]:
    """Evaluate all active scheduled triggers and fire due ones.

    Iterates over active cron, scheduled, datetime, and recurring
    triggers, evaluates each against the current time, and fires
    those that are due.

    :returns: Result dict with counts.
    """
    logger.info("Task started: %s", self.name)

    from apps.workflows_v2.models.trigger import WorkflowTrigger
    from apps.workflows_v2.services.trigger_engine import (
        list_active_triggers,
        evaluate_trigger,
    )

    scheduled_types = [
        WorkflowTrigger.TYPE_CRON,
        WorkflowTrigger.TYPE_SCHEDULED,
        WorkflowTrigger.TYPE_DATETIME,
        WorkflowTrigger.TYPE_RECURRING,
    ]

    fired = 0
    skipped = 0

    for trigger_type in scheduled_types:
        triggers = list_active_triggers(trigger_type=trigger_type)
        for trigger in triggers:
            try:
                should_fire = evaluate_trigger(trigger)
                if should_fire:
                    trigger.record_trigger()
                    execute_workflow.delay(
                        workflow_id=trigger.workflow_id,
                        tenant_id=trigger.workflow.tenant_id,
                        trigger_data={"trigger_type": trigger_type, "trigger_id": trigger.id},
                        trigger_type=trigger_type,
                    )
                    fired += 1
                else:
                    skipped += 1
            except Exception as exc:
                logger.error("Trigger evaluation error for %s: %s", trigger.id, exc)
                skipped += 1

    result: dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "fired": fired,
        "skipped": skipped,
    }
    logger.info("Task completed: %s (fired=%s, skipped=%s)", self.name, fired, skipped)
    return result


@shared_task(bind=True, max_retries=3)
def check_approval_timeouts(self) -> dict[str, Any]:
    """Check for pending approvals that have exceeded their deadline.

    Escalates or times out approvals past their deadline.

    :returns: Result dict with count of processed approvals.
    """
    logger.info("Task started: %s", self.name)

    from apps.workflows_v2.services.human_loop import find_pending_timeouts, handle_timeout

    timed_out = find_pending_timeouts()
    count = 0
    for approval in timed_out:
        try:
            handle_timeout(approval)
            count += 1
        except Exception as exc:
            logger.error("Timeout handling error for approval %s: %s", approval.id, exc)

    result: dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "timed_out_count": count,
    }
    logger.info("Task completed: %s (timed out %s approvals)", self.name, count)
    return result


@shared_task(bind=True, max_retries=3)
def sync_vortex_executions(self) -> dict[str, Any]:
    """Synchronize running executions with Vortex status.

    Polls Vortex for the latest status of all running executions
    and updates local state.

    :returns: Result dict with sync counts.
    """
    logger.info("Task started: %s", self.name)

    import asyncio

    from apps.workflows_v2.models.execution import WorkflowExecution
    from apps.workflows_v2.services.vortex_integration import sync_execution_status

    running = WorkflowExecution.objects.filter(
        status=WorkflowExecution.STATUS_RUNNING,
    ).exclude(run_id="")

    synced = 0
    failed = 0

    for execution in running:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # Note: This requires a token; in production, use a service token
            result = loop.run_until_complete(
                sync_execution_status(execution, "")
            )
            loop.close()
            synced += 1
            logger.debug("Synced execution %s: %s", execution.id, result)
        except Exception as exc:
            failed += 1
            logger.error("Sync error for execution %s: %s", execution.id, exc)

    result: dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "synced": synced,
        "failed": failed,
    }
    logger.info("Task completed: %s (synced=%s, failed=%s)", self.name, synced, failed)
    return result
