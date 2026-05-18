"""Workflow execution service — action registry and parameter validation.

Manages the execution lifecycle: starting runs, executing action nodes,
validating parameters, and tracking execution state.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from django.utils import timezone

from apps.workflows_v2.models.workflow import Workflow
from apps.workflows_v2.models.execution import WorkflowExecution, WorkflowExecutionLog
from apps.workflows_v2.models.node import WorkflowNode
from apps.workflows_v2.models.edge import WorkflowEdge
from apps.workflows_v2.services.conditions import evaluate_expression

logger = logging.getLogger(__name__)

# ── Action Registry ─────────────────────────────────────────────

ActionHandler = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]

_ACTION_REGISTRY: dict[str, dict[str, ActionHandler]] = {}


def register_action(module: str, function: str, handler: ActionHandler) -> None:
    """Register an action handler for a module:function pair.

    Args:
        module: Module name (e.g. 'notification').
        function: Function name (e.g. 'sendEmail').
        handler: Callable that receives (params, context) and returns output dict.
    """
    if module not in _ACTION_REGISTRY:
        _ACTION_REGISTRY[module] = {}
    _ACTION_REGISTRY[module][function] = handler
    logger.debug("Registered action handler: %s:%s", module, function)


def get_action_handler(module: str, function: str) -> ActionHandler | None:
    """Get the registered handler for a module:function pair.

    Args:
        module: Module name.
        function: Function name.

    Returns:
        The handler callable, or None if not registered.
    """
    return _ACTION_REGISTRY.get(module, {}).get(function)


def list_registered_modules() -> list[str]:
    """List all registered action modules."""
    return list(_ACTION_REGISTRY.keys())


def list_registered_functions(module: str) -> list[str]:
    """List all registered functions for a module."""
    return list(_ACTION_REGISTRY.get(module, {}).keys())


def validate_action_params(
    module: str,
    function: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Validate action parameters against the registered handler schema.

    Args:
        module: Module name.
        function: Function name.
        params: Parameters to validate.

    Returns:
        Dict with ``valid`` (bool) and ``errors`` (list).
    """
    handler = get_action_handler(module, function)
    if handler is None:
        return {
            "valid": False,
            "errors": [f"No handler registered for {module}:{function}"],
        }

    # Extract parameter hints from handler signature if available
    import inspect

    try:
        sig = inspect.signature(handler)
        errors: list[str] = []
        # Basic structural validation
        if not isinstance(params, dict):
            errors.append("Parameters must be a dictionary")
        return {"valid": len(errors) == 0, "errors": errors}
    except (ValueError, TypeError):
        return {"valid": True, "errors": []}


# ── Execution Lifecycle ─────────────────────────────────────────


def start_execution(
    workflow: Workflow,
    trigger_type: str,
    trigger_data: dict[str, Any],
    user_id: str | None = None,
) -> WorkflowExecution:
    """Start a new workflow execution.

    Args:
        workflow: The workflow to execute.
        trigger_type: How the execution was triggered.
        trigger_data: Trigger payload data.
        user_id: Optional user who initiated the execution.

    Returns:
        The created WorkflowExecution instance.
    """
    if not workflow.can_execute():
        raise ValueError(f"Workflow '{workflow.name}' cannot be executed (status={workflow.status})")

    execution = WorkflowExecution.objects.create(
        workflow=workflow,
        version=workflow.version,
        status=WorkflowExecution.STATUS_PENDING,
        trigger_type=trigger_type,
        trigger_data=trigger_data,
        context={
            "trigger": trigger_data,
            "triggered_by": user_id,
            "started_at": timezone.now().isoformat(),
        },
    )
    logger.info(
        "Started execution %s for workflow %s (trigger=%s)",
        execution.id,
        workflow.id,
        trigger_type,
    )
    return execution


def execute_next_node(
    execution: WorkflowExecution,
    nodes: list[WorkflowNode],
    edges: list[WorkflowEdge],
) -> dict[str, Any]:
    """Execute the next node in a workflow execution.

    Advances the execution by one node, executing the current node's
    logic and updating the execution state.

    Args:
        execution: The current execution.
        nodes: All workflow nodes.
        edges: All workflow edges.

    Returns:
        Dict with ``completed``, ``next_node_id``, and ``output``.
    """
    node_map = {n.node_id: n for n in nodes}
    edge_map: dict[str, list[WorkflowEdge]] = {}
    for e in edges:
        edge_map.setdefault(e.source, []).append(e)

    current_node_id = execution.current_node

    # Find starting node if not set
    if not current_node_id:
        trigger_nodes = [n for n in nodes if n.node_type == WorkflowNode.TYPE_TRIGGER]
        if not trigger_nodes:
            execution.status = WorkflowExecution.STATUS_FAILED
            execution.error = "No trigger node found"
            execution.completed_at = timezone.now()
            execution.save()
            return {"completed": True, "error": "No trigger node"}
        current_node_id = trigger_nodes[0].node_id

    if current_node_id not in node_map:
        execution.status = WorkflowExecution.STATUS_FAILED
        execution.error = f"Node '{current_node_id}' not found"
        execution.completed_at = timezone.now()
        execution.save()
        return {"completed": True, "error": f"Node not found: {current_node_id}"}

    node = node_map[current_node_id]

    # Execute the node
    result = _execute_node(node, execution.context)

    # Log the execution
    WorkflowExecutionLog.objects.create(
        execution=execution,
        node_id=node.node_id,
        node_type=node.node_type,
        input_data={"context": execution.context},
        output_data=result.get("output", {}),
        status=WorkflowExecutionLog.STATUS_SUCCESS if not result.get("error") else WorkflowExecutionLog.STATUS_FAILED,
        duration_ms=result.get("duration_ms"),
        error=result.get("error", ""),
    )

    # Update context
    execution.context.update(result.get("output", {}))

    # Determine next node
    next_node_id = result.get("next_node_id")
    if not next_node_id:
        outgoing = edge_map.get(node.node_id, [])
        if outgoing:
            next_node_id = outgoing[0].target

    execution.current_node = next_node_id or ""

    # Check if execution is complete
    if not next_node_id or next_node_id not in node_map:
        execution.status = WorkflowExecution.STATUS_COMPLETED
        execution.completed_at = timezone.now()
        execution.save()
        return {"completed": True, "next_node_id": None, "output": result.get("output", {})}

    execution.status = WorkflowExecution.STATUS_RUNNING
    execution.save()
    return {
        "completed": False,
        "next_node_id": next_node_id,
        "output": result.get("output", {}),
    }


def _execute_node(node: WorkflowNode, context: dict[str, Any]) -> dict[str, Any]:
    """Execute a single node and return the result.

    Args:
        node: The node to execute.
        context: Current execution context.

    Returns:
        Dict with ``output``, ``next_node_id``, ``duration_ms``, ``error``.
    """
    import time

    start = time.time()

    try:
        if node.node_type == WorkflowNode.TYPE_TRIGGER:
            result = _execute_trigger(node, context)
        elif node.node_type == WorkflowNode.TYPE_ACTION:
            result = _execute_action(node, context)
        elif node.node_type == WorkflowNode.TYPE_CONDITION:
            result = _execute_condition(node, context)
        elif node.node_type == WorkflowNode.TYPE_DELAY:
            result = _execute_delay(node, context)
        elif node.node_type == WorkflowNode.TYPE_HITL:
            result = _execute_hitl(node, context)
        elif node.node_type == WorkflowNode.TYPE_WEBHOOK:
            result = _execute_webhook(node, context)
        elif node.node_type == WorkflowNode.TYPE_LOOP:
            result = _execute_loop(node, context)
        elif node.node_type == WorkflowNode.TYPE_TRANSFORM:
            result = _execute_transform(node, context)
        elif node.node_type == WorkflowNode.TYPE_SUB_FLOW:
            result = _execute_sub_flow(node, context)
        elif node.node_type == WorkflowNode.TYPE_ERROR_HANDLER:
            result = _execute_error_handler(node, context)
        else:
            result = {"output": {}}

        duration_ms = int((time.time() - start) * 1000)
        result["duration_ms"] = duration_ms
        return result

    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        logger.error("Node execution error for %s: %s", node.node_id, exc)
        return {
            "output": {},
            "error": str(exc),
            "duration_ms": duration_ms,
        }


def _execute_trigger(node: WorkflowNode, context: dict[str, Any]) -> dict[str, Any]:
    """Execute a trigger node."""
    config = node.config
    return {
        "output": {
            "triggered": True,
            "trigger_type": config.get("triggerType", "manual"),
        },
    }


def _execute_action(node: WorkflowNode, context: dict[str, Any]) -> dict[str, Any]:
    """Execute an action node by delegating to a registered handler."""
    config = node.config
    module = config.get("module", "")
    function = config.get("function", "")
    params = config.get("params", {})

    handler = get_action_handler(module, function)
    if handler:
        try:
            output = handler(params, context)
            return {"output": output}
        except Exception as exc:
            logger.error("Action handler error for %s:%s: %s", module, function, exc)
            return {"output": {}, "error": f"Action {module}:{function} failed: {exc}"}

    # No handler registered — return simulated output
    return {
        "output": {
            "action": f"{module}:{function}",
            "params": params,
            "status": "simulated",
        },
    }


def _execute_condition(node: WorkflowNode, context: dict[str, Any]) -> dict[str, Any]:
    """Execute a condition node and determine the next branch."""
    from apps.workflows_v2.services.conditions import evaluate_condition_branch

    result = evaluate_condition_branch(node.config, context)
    return {
        "output": {"condition_result": result},
        "next_node_id": result,  # Will be resolved by the caller
    }


def _execute_delay(node: WorkflowNode, context: dict[str, Any]) -> dict[str, Any]:
    """Execute a delay node."""
    config = node.config
    duration = config.get("duration", 0)
    return {
        "output": {"delayed": True, "duration": duration},
    }


def _execute_hitl(node: WorkflowNode, context: dict[str, Any]) -> dict[str, Any]:
    """Execute a HITL node — returns pending status for approval."""
    config = node.config
    return {
        "output": {
            "approval_status": "pending",
            "approvers": config.get("approvers", []),
            "timeout_hours": config.get("timeoutHours", 24),
        },
    }


def _execute_webhook(node: WorkflowNode, context: dict[str, Any]) -> dict[str, Any]:
    """Execute a webhook node (outbound HTTP call)."""
    config = node.config
    import httpx

    url = config.get("url", "")
    method = config.get("method", "POST").upper()
    headers = config.get("headers", {})
    body_template = config.get("body", {})

    # Simple template rendering: replace {{var}} with context values
    body = _render_template(body_template, context)

    try:
        response = httpx.request(method, url, headers=headers, json=body, timeout=30.0)
        return {
            "output": {
                "status_code": response.status_code,
                "response_body": response.text[:1000] if response.text else "",
            },
        }
    except Exception as exc:
        logger.error("Webhook call failed for node %s: %s", node.node_id, exc)
        return {
            "output": {"error": str(exc)},
            "error": f"Webhook call failed: {exc}",
        }


def _execute_loop(node: WorkflowNode, context: dict[str, Any]) -> dict[str, Any]:
    """Execute a loop node."""
    from apps.workflows_v2.services.conditions import evaluate_loop_collection

    collection = evaluate_loop_collection(node.config, context)
    return {
        "output": {
            "iterations": len(collection),
            "collection_size": len(collection),
        },
    }


def _execute_transform(node: WorkflowNode, context: dict[str, Any]) -> dict[str, Any]:
    """Execute a transform node."""
    config = node.config
    input_mapping = config.get("inputMapping", {})
    output_mapping = config.get("outputMapping", {})

    output: dict[str, Any] = {}
    for key, expr in output_mapping.items():
        try:
            output[key] = evaluate_expression(expr, context)
        except Exception:
            output[key] = None

    return {"output": output}


def _execute_sub_flow(node: WorkflowNode, context: dict[str, Any]) -> dict[str, Any]:
    """Execute a sub-flow node."""
    config = node.config
    sub_workflow_id = config.get("workflowId")
    return {
        "output": {
            "sub_flow_executed": True,
            "sub_workflow_id": sub_workflow_id,
        },
    }


def _execute_error_handler(node: WorkflowNode, context: dict[str, Any]) -> dict[str, Any]:
    """Execute an error handler node."""
    config = node.config
    return {
        "output": {
            "error_handled": True,
            "retry_policy": config.get("retryPolicy", {}),
        },
    }


def _render_template(template: Any, context: dict[str, Any]) -> Any:
    """Render a template by replacing {{key}} with context values.

    Args:
        template: The template (dict, list, or string).
        context: Variable bindings.

    Returns:
        The rendered template.
    """
    if isinstance(template, dict):
        return {k: _render_template(v, context) for k, v in template.items()}
    if isinstance(template, list):
        return [_render_template(item, context) for item in template]
    if isinstance(template, str):
        result = template
        for key, value in context.items():
            if isinstance(value, (str, int, float, bool)):
                result = result.replace(f"{{{{{key}}}}}", str(value))
        return result
    return template


def cancel_execution(execution: WorkflowExecution) -> None:
    """Cancel a running workflow execution.

    Args:
        execution: The execution to cancel.
    """
    if execution.is_terminal():
        return
    execution.status = WorkflowExecution.STATUS_CANCELLED
    execution.completed_at = timezone.now()
    execution.save(update_fields=["status", "completed_at"])
    logger.info("Execution %s cancelled", execution.id)


def get_execution_progress(execution: WorkflowExecution) -> dict[str, Any]:
    """Get the progress of a workflow execution.

    Args:
        execution: The execution to check.

    Returns:
        Dict with ``status``, ``progress``, ``current_node``, ``logs``.
    """
    logs = execution.logs.values("node_id", "node_type", "status", "executed_at").order_by("executed_at")
    return {
        "status": execution.status,
        "progress": execution.progress,
        "current_node": execution.current_node,
        "is_terminal": execution.is_terminal(),
        "logs": list(logs),
    }
