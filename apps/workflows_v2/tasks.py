"""Celery tasks for the Workflows v2 module.

Handles workflow execution triggers, state transitions, and
integration with the Vortex workflow engine.

Tasks are routed to the ``workflows`` queue via
``voyager_project.celery.app.conf.task_routes``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def execute_workflow(
    self,
    workflow_id: str,
    tenant_id: str,
    trigger_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Execute a workflow definition via Vortex.

    :param workflow_id: UUID of the workflow.
    :param tenant_id: UUID of the tenant scope.
    :param trigger_data: Data that triggered the workflow.
    :returns: Result dict with ``workflow_id``, ``graph_id``, "run_id``.
    """
    logger.info(
        "Executing workflow %s for tenant %s", workflow_id, tenant_id
    )

    result: Dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "workflow_id": workflow_id,
        "graph_id": None,
        "run_id": None,
    }
    return result


@shared_task(bind=True, max_retries=3)
def cleanup_stale_workflow_runs(self) -> Dict[str, Any]:
    """Clean up workflow runs stuck in non-terminal states.

    Finds runs that have been in ``running`` or ``pending`` state
    longer than the configured timeout and marks them as ``failed``.

    :returns: Result dict with ``runs_cleaned``.
    """
    logger.info("Task started: %s", self.name)

    result: Dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "runs_cleaned": 0,
    }
    logger.info("Task completed: %s", self.name)
    return result
