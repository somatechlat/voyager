"""Vortex integration service — compile workflows to GraphDSL and execute.

Translates workflow definitions to Vortex GraphDSL, submits them
for execution, and handles execution callbacks and monitoring.
"""

from __future__ import annotations

import logging
from typing import Any

from apps.workflows_v2.models.execution import WorkflowExecution
from apps.workflows_v2.models.node import WorkflowNode
from apps.workflows_v2.models.workflow import Workflow

logger = logging.getLogger(__name__)


NODE_TYPE_MAP: dict[str, str] = {
    WorkflowNode.TYPE_TRIGGER: "trigger",
    WorkflowNode.TYPE_ACTION: "action",
    WorkflowNode.TYPE_CONDITION: "condition",
    WorkflowNode.TYPE_LOOP: "loop",
    WorkflowNode.TYPE_DELAY: "delay",
    WorkflowNode.TYPE_TRANSFORM: "transform",
    WorkflowNode.TYPE_HITL: "human_approval",
    WorkflowNode.TYPE_WEBHOOK: "webhook",
    WorkflowNode.TYPE_SUB_FLOW: "subflow",
    WorkflowNode.TYPE_ERROR_HANDLER: "error_handler",
}


def compile_to_graph_dsl(workflow: Workflow) -> dict[str, Any]:
    """Compile a workflow definition to Vortex GraphDSL.

    Translates the workflow's nodes and edges into the Vortex-native
    graph format for execution on the Vortex engine.

    Args:
        workflow: The workflow to compile.

    Returns:
        GraphDSL dictionary with ``nodes``, ``edges``, and ``config``.
    """
    nodes = list(workflow.workflow_nodes.all())
    edges = list(workflow.workflow_edges.all())

    graph_nodes: list[dict[str, Any]] = []
    for node in nodes:
        graph_node: dict[str, Any] = {
            "id": node.node_id,
            "type": NODE_TYPE_MAP.get(node.node_type, node.node_type),
            "label": node.label or node.node_id,
            "config": node.config,
        }
        if node.position:
            graph_node["position"] = node.position
        graph_nodes.append(graph_node)

    graph_edges: list[dict[str, Any]] = []
    for edge in edges:
        graph_edge: dict[str, Any] = {
            "from": edge.source,
            "to": edge.target,
        }
        if edge.label:
            graph_edge["label"] = edge.label
        if edge.condition:
            graph_edge["condition"] = edge.condition
        graph_edges.append(graph_edge)

    graph_dsl: dict[str, Any] = {
        "name": workflow.name,
        "version": workflow.version,
        "nodes": graph_nodes,
        "edges": graph_edges,
        "config": workflow.config or {},
    }

    if workflow.trigger_config:
        graph_dsl["trigger_config"] = workflow.trigger_config

    return graph_dsl


async def submit_workflow_to_vortex(
    workflow: Workflow,
    token: str,
    priority: str | None = None,
) -> str:
    """Submit a compiled workflow to Vortex for execution.

    Args:
        workflow: The workflow to submit.
        token: Bearer JWT token from Keycloak.
        priority: Optional execution priority.

    Returns:
        The Vortex graph_id.

    Raises:
        ValueError: If Vortex client is unavailable.
        RuntimeError: If Vortex returns an error.
    """
    from vortex_bridge.client import vortex_client

    graph_dsl = compile_to_graph_dsl(workflow)

    try:
        graph_id = await vortex_client.submit_graph(graph_dsl, token, priority=priority)
        logger.info(
            "Workflow %s submitted to Vortex: graph_id=%s",
            workflow.id,
            graph_id,
        )
        return graph_id
    except Exception as exc:
        logger.error("Failed to submit workflow %s to Vortex: %s", workflow.id, exc)
        raise RuntimeError(f"Vortex submission failed: {exc}") from exc


async def execute_on_vortex(
    graph_id: str,
    token: str,
    execution: WorkflowExecution | None = None,
) -> str:
    """Start execution of a submitted graph on Vortex.

    Args:
        graph_id: The Vortex graph ID.
        token: Bearer JWT token.
        execution: Optional execution record to update.

    Returns:
        The Vortex run_id.
    """
    from vortex_bridge.client import vortex_client

    try:
        run_id = await vortex_client.execute_graph(graph_id, token)
        if execution:
            execution.graph_id = graph_id
            execution.run_id = run_id
            execution.status = WorkflowExecution.STATUS_RUNNING
            execution.save(update_fields=["graph_id", "run_id", "status"])
        logger.info("Vortex execution started: graph_id=%s run_id=%s", graph_id, run_id)
        return run_id
    except Exception as exc:
        logger.error("Vortex execution failed for graph %s: %s", graph_id, exc)
        if execution:
            execution.status = WorkflowExecution.STATUS_FAILED
            execution.error = f"Vortex execution failed: {exc}"
            execution.save(update_fields=["status", "error"])
        raise RuntimeError(f"Vortex execution failed: {exc}") from exc


async def get_execution_status(
    run_id: str,
    token: str,
) -> dict[str, Any]:
    """Check the status of a Vortex graph execution.

    Args:
        run_id: The Vortex run ID.
        token: Bearer JWT token.

    Returns:
        Dict with ``status``, ``progress``, and ``current_node``.
    """
    from vortex_bridge.client import vortex_client

    try:
        status = await vortex_client.get_run_status(run_id, token)
        return status
    except Exception as exc:
        logger.error("Failed to get status for run %s: %s", run_id, exc)
        return {
            "run_id": run_id,
            "status": "unknown",
            "progress": 0.0,
            "error": str(exc),
        }


async def cancel_vortex_execution(run_id: str, token: str) -> bool:
    """Cancel a running Vortex graph execution.

    Args:
        run_id: The Vortex run ID.
        token: Bearer JWT token.

    Returns:
        True if cancellation was accepted.
    """
    from vortex_bridge.client import vortex_client

    try:
        result = await vortex_client.cancel_run(run_id, token)
        logger.info("Vortex run %s cancelled: %s", run_id, result)
        return result
    except Exception as exc:
        logger.error("Failed to cancel Vortex run %s: %s", run_id, exc)
        return False


async def sync_execution_status(
    execution: WorkflowExecution,
    token: str,
) -> dict[str, Any]:
    """Synchronize a local execution record with Vortex status.

    Polls Vortex for the latest status and updates the local
    execution record accordingly.

    Args:
        execution: The local execution record.
        token: Bearer JWT token.

    Returns:
        Updated status dict.
    """
    if not execution.run_id:
        return {"error": "No run_id associated with execution"}

    vortex_status = await get_execution_status(execution.run_id, token)

    vortex_state = vortex_status.get("status", "unknown")
    progress = vortex_status.get("progress", 0.0)
    current_node = vortex_status.get("current_node", "")

    # Map Vortex status to our status
    status_map = {
        "running": WorkflowExecution.STATUS_RUNNING,
        "completed": WorkflowExecution.STATUS_COMPLETED,
        "failed": WorkflowExecution.STATUS_FAILED,
        "cancelled": WorkflowExecution.STATUS_CANCELLED,
        "pending": WorkflowExecution.STATUS_PENDING,
    }

    new_status = status_map.get(vortex_state, execution.status)

    execution.status = new_status
    execution.current_node = current_node
    if new_status in (
        WorkflowExecution.STATUS_COMPLETED,
        WorkflowExecution.STATUS_FAILED,
        WorkflowExecution.STATUS_CANCELLED,
    ):
        from django.utils import timezone

        execution.completed_at = timezone.now()
    execution.save()

    return {
        "execution_id": execution.id,
        "vortex_status": vortex_state,
        "local_status": new_status,
        "progress": progress,
        "current_node": current_node,
    }


def handle_execution_callback(
    execution: WorkflowExecution,
    callback_data: dict[str, Any],
) -> None:
    """Handle a callback from Vortex about an execution event.

    Updates the execution state based on callback data from Vortex
    (node completion, errors, human approval requests).

    Args:
        execution: The local execution record.
        callback_data: Callback payload from Vortex.
    """
    event_type = callback_data.get("event_type", "")

    if event_type == "node_complete":
        node_id = callback_data.get("node_id", "")
        output = callback_data.get("output", {})
        execution.context.update(output)
        execution.current_node = node_id
        execution.save(update_fields=["context", "current_node"])
        logger.info("Node %s completed in execution %s", node_id, execution.id)

    elif event_type == "node_error":
        node_id = callback_data.get("node_id", "")
        error = callback_data.get("error", "")
        execution.error = f"Node {node_id}: {error}"
        execution.status = WorkflowExecution.STATUS_FAILED
        execution.save(update_fields=["error", "status"])
        logger.error("Node %s error in execution %s: %s", node_id, execution.id, error)

    elif event_type == "human_approval_required":
        node_id = callback_data.get("node_id", "")
        execution.status = WorkflowExecution.STATUS_WAITING_HITL
        execution.current_node = node_id
        execution.save(update_fields=["status", "current_node"])
        logger.info("Human approval required for execution %s node %s", execution.id, node_id)

    elif event_type == "execution_complete":
        execution.status = WorkflowExecution.STATUS_COMPLETED
        execution.completed_at = timezone.now()
        execution.save(update_fields=["status", "completed_at"])
        logger.info("Execution %s completed", execution.id)

    elif event_type == "execution_failed":
        execution.status = WorkflowExecution.STATUS_FAILED
        execution.error = callback_data.get("error", "Unknown error")
        execution.completed_at = timezone.now()
        execution.save(update_fields=["status", "error", "completed_at"])
        logger.error("Execution %s failed: %s", execution.id, execution.error)

    else:
        logger.warning("Unknown callback event type: %s", event_type)
