"""Workflow validation and simulation service.

Performs structural validation (BFS reachability, cycle detection,
condition checks, HITL checks) and execution simulation.
"""

from __future__ import annotations

import copy
import logging
from collections import deque
from typing import Any

from apps.workflows_v2.models.workflow import Workflow, WorkflowVersion
from apps.workflows_v2.models.node import WorkflowNode
from apps.workflows_v2.models.edge import WorkflowEdge

logger = logging.getLogger(__name__)


def validate_workflow(workflow: Workflow) -> dict[str, Any]:
    """Validate a workflow definition against structural rules.

    Performs six validation checks:
    1. At least one trigger node exists.
    2. All nodes are reachable from a trigger via BFS.
    3. No circular dependencies (except loop nodes).
    4. Condition nodes have at least 2 outgoing edges.
    5. HITL nodes have timeout configured.
    6. Action nodes reference valid modules/functions.

    Args:
        workflow: The workflow to validate.

    Returns:
        Dict with ``valid`` (bool) and ``errors`` (list of error dicts).
    """
    errors: list[dict[str, Any]] = []
    nodes = list(workflow.workflow_nodes.all())
    edges = list(workflow.workflow_edges.all())
    node_map = {n.node_id: n for n in nodes}
    edge_map: dict[str, list[WorkflowEdge]] = {}
    for e in edges:
        edge_map.setdefault(e.source, []).append(e)

    # 1. Must have at least one trigger
    trigger_nodes = [n for n in nodes if n.node_type == WorkflowNode.TYPE_TRIGGER]
    if not trigger_nodes:
        errors.append(
            {"type": "no_trigger", "message": "Workflow must have at least one trigger node"}
        )

    # 2. All nodes must be reachable from a trigger
    if trigger_nodes:
        reachable = _bfs_reachable(trigger_nodes[0].node_id, edge_map)
        unreachable = [n.node_id for n in nodes if n.node_id not in reachable]
        if unreachable:
            errors.append(
                {
                    "type": "unreachable_nodes",
                    "message": f"Nodes unreachable from trigger: {unreachable}",
                    "nodes": unreachable,
                }
            )

    # 3. No circular dependencies (except loop nodes)
    loop_ids = {n.node_id for n in nodes if n.node_type == WorkflowNode.TYPE_LOOP}
    cycle = _detect_cycle(node_map, edges, exclude_nodes=loop_ids)
    if cycle:
        errors.append(
            {
                "type": "circular_dependency",
                "message": f"Circular dependency detected: {' -> '.join(cycle)}",
                "cycle": cycle,
            }
        )

    # 4. Condition nodes must have >= 2 outgoing edges
    for node in nodes:
        if node.node_type == WorkflowNode.TYPE_CONDITION:
            outgoing = edge_map.get(node.node_id, [])
            if len(outgoing) < 2:
                errors.append(
                    {
                        "type": "condition_needs_branches",
                        "message": f"Condition node '{node.node_id}' needs >= 2 outgoing connections",
                        "node_id": node.node_id,
                    }
                )

    # 5. HITL nodes must have timeout configured
    for node in nodes:
        if node.node_type == WorkflowNode.TYPE_HITL:
            timeout = node.config.get("timeoutHours")
            if not timeout:
                errors.append(
                    {
                        "type": "hitl_missing_timeout",
                        "message": f"HITL node '{node.node_id}' must have timeoutHours configured",
                        "node_id": node.node_id,
                    }
                )

    # 6. Action nodes must have module and function
    for node in nodes:
        if node.node_type == WorkflowNode.TYPE_ACTION:
            if not node.config.get("module"):
                errors.append(
                    {
                        "type": "invalid_module",
                        "message": f"Action node '{node.node_id}' missing 'module' in config",
                        "node_id": node.node_id,
                    }
                )
            if not node.config.get("function"):
                errors.append(
                    {
                        "type": "invalid_function",
                        "message": f"Action node '{node.node_id}' missing 'function' in config",
                        "node_id": node.node_id,
                    }
                )

    return {"valid": len(errors) == 0, "errors": errors}


def _bfs_reachable(
    start_node_id: str,
    edge_map: dict[str, list[WorkflowEdge]],
) -> set[str]:
    """Return all node IDs reachable from start_node_id via BFS."""
    visited: set[str] = {start_node_id}
    queue: deque[str] = deque([start_node_id])
    while queue:
        current = queue.popleft()
        for edge in edge_map.get(current, []):
            if edge.target not in visited:
                visited.add(edge.target)
                queue.append(edge.target)
    return visited


def _detect_cycle(
    node_map: dict[str, WorkflowNode],
    edges: list[WorkflowEdge],
    exclude_nodes: set[str],
) -> list[str] | None:
    """Detect cycles in the workflow graph, excluding loop nodes."""
    adj: dict[str, list[str]] = {}
    for node_id in node_map:
        if node_id not in exclude_nodes:
            adj[node_id] = []
    for edge in edges:
        if edge.source not in exclude_nodes and edge.target not in exclude_nodes:
            adj.setdefault(edge.source, []).append(edge.target)

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {n: WHITE for n in adj}
    parent: dict[str, str | None] = {n: None for n in adj}

    def dfs(node: str) -> list[str] | None:
        color[node] = GRAY
        for neighbor in adj.get(node, []):
            if neighbor not in color:
                continue
            if color[neighbor] == GRAY:
                cycle: list[str] = [neighbor]
                current = node
                while current != neighbor and current is not None:
                    cycle.append(current)
                    current = parent.get(current)
                cycle.append(neighbor)
                cycle.reverse()
                return cycle
            if color[neighbor] == WHITE:
                parent[neighbor] = node
                result = dfs(neighbor)
                if result:
                    return result
        color[node] = BLACK
        return None

    for node_id in adj:
        if color[node_id] == WHITE:
            result = dfs(node_id)
            if result:
                return result
    return None


def simulate_workflow(
    workflow: Workflow,
    test_data: dict[str, Any],
) -> dict[str, Any]:
    """Simulate a workflow execution with test data.

    Walks the workflow graph from the trigger node, simulating each
    node's execution and collecting a simulation log.

    Args:
        workflow: The workflow to simulate.
        test_data: Test input data merged into the execution context.

    Returns:
        Dict with ``simulationLog`` and ``finalContext``.
    """
    simulation_log: list[dict[str, Any]] = []
    context: dict[str, Any] = copy.deepcopy(test_data)
    nodes = list(workflow.workflow_nodes.all())
    edges = list(workflow.workflow_edges.all())

    if not nodes:
        return {"simulationLog": [], "finalContext": context}

    node_map = {n.node_id: n for n in nodes}
    edge_map: dict[str, list[WorkflowEdge]] = {}
    for e in edges:
        edge_map.setdefault(e.source, []).append(e)

    trigger_nodes = [n for n in nodes if n.node_type == WorkflowNode.TYPE_TRIGGER]
    if not trigger_nodes:
        return {"simulationLog": [], "finalContext": context, "error": "No trigger node"}

    current_node = trigger_nodes[0]
    visited_count: dict[str, int] = {}
    max_steps = 500
    step = 0

    while current_node and step < max_steps:
        step += 1
        node_id = current_node.node_id
        visited_count[node_id] = visited_count.get(node_id, 0) + 1
        if visited_count[node_id] > 10:
            simulation_log.append(
                {
                    "nodeId": node_id,
                    "nodeType": current_node.node_type,
                    "status": "skipped",
                    "output": {},
                    "error": "Loop limit exceeded in simulation",
                }
            )
            break

        result = _simulate_node(current_node, context)
        simulation_log.append(
            {
                "nodeId": node_id,
                "nodeType": current_node.node_type,
                "input": copy.deepcopy(context),
                "output": result.get("output", {}),
                "duration": result.get("mockDuration", 0),
                "decision": result.get("decision"),
                "status": "success",
            }
        )
        context.update(result.get("output", {}))
        next_node_id = _get_next_node_id(current_node, context, edge_map)
        current_node = node_map.get(next_node_id) if next_node_id else None

    return {"simulationLog": simulation_log, "finalContext": context}


def _simulate_node(
    node: WorkflowNode,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Simulate execution of a single node."""
    config = node.config
    nt = node.node_type

    if nt == WorkflowNode.TYPE_TRIGGER:
        return {"output": {"triggered": True}, "mockDuration": 10}
    elif nt == WorkflowNode.TYPE_ACTION:
        return {
            "output": {f"action_{config.get('function', 'result')}": "simulated"},
            "mockDuration": 100,
        }
    elif nt == WorkflowNode.TYPE_CONDITION:
        return {
            "output": {"condition_result": "true"},
            "mockDuration": 20,
            "decision": "true",
        }
    elif nt == WorkflowNode.TYPE_DELAY:
        duration = config.get("duration", 0)
        return {"output": {"delayed": True, "duration": duration}, "mockDuration": duration}
    elif nt == WorkflowNode.TYPE_HITL:
        return {
            "output": {"approval": "simulated_approved"},
            "mockDuration": 50,
            "decision": "approved",
        }
    elif nt == WorkflowNode.TYPE_WEBHOOK:
        return {"output": {"webhook_status": 200, "response": {}}, "mockDuration": 200}
    elif nt == WorkflowNode.TYPE_LOOP:
        return {"output": {"iterations": 3, "loop_result": "simulated"}, "mockDuration": 300}
    elif nt == WorkflowNode.TYPE_TRANSFORM:
        return {"output": {"transformed": True}, "mockDuration": 30}
    elif nt == WorkflowNode.TYPE_SUB_FLOW:
        return {"output": {"sub_flow_result": "simulated"}, "mockDuration": 150}
    elif nt == WorkflowNode.TYPE_ERROR_HANDLER:
        return {"output": {"error_handled": True}, "mockDuration": 40}
    return {"output": {}, "mockDuration": 0}


def _get_next_node_id(
    node: WorkflowNode,
    context: dict[str, Any],
    edge_map: dict[str, list[WorkflowEdge]],
) -> str | None:
    """Determine the next node ID based on current node and context."""
    outgoing = edge_map.get(node.node_id, [])
    if not outgoing:
        return None
    if node.node_type in (WorkflowNode.TYPE_CONDITION, WorkflowNode.TYPE_HITL):
        return outgoing[0].target if outgoing else None
    return outgoing[0].target


def publish_version(
    workflow: Workflow,
    published_by: str,
    changelog: str = "",
) -> WorkflowVersion:
    """Publish the current workflow state as a new version.

    Creates a WorkflowVersion snapshot and increments the workflow's
    version counter.

    Args:
        workflow: The workflow to publish.
        published_by: User ID of the publisher.
        changelog: Description of changes.

    Returns:
        The created WorkflowVersion instance.
    """
    new_version = workflow.version + 1
    snapshot = WorkflowVersion.objects.create(
        workflow=workflow,
        version=new_version,
        nodes=copy.deepcopy(workflow.nodes),
        connections=copy.deepcopy(workflow.connections),
        changelog=changelog,
        published_by=published_by,
    )
    workflow.version = new_version
    workflow.status = Workflow.STATUS_ACTIVE
    workflow.save(update_fields=["version", "status", "updated_at"])
    return snapshot


def compare_versions(
    version_a: WorkflowVersion,
    version_b: WorkflowVersion,
) -> dict[str, Any]:
    """Compare two workflow versions and return a diff.

    Args:
        version_a: First version to compare.
        version_b: Second version to compare.

    Returns:
        Dict with nodes added, removed, modified and connections
        added, removed.
    """
    nodes_a = {n.get("node_id", n.get("id", str(i))): n for i, n in enumerate(version_a.nodes)}
    nodes_b = {n.get("node_id", n.get("id", str(i))): n for i, n in enumerate(version_b.nodes)}
    conn_a = {(c.get("source", c.get("from")), c.get("target", c.get("to"))): c
              for c in version_a.connections}
    conn_b = {(c.get("source", c.get("from")), c.get("target", c.get("to"))): c
              for c in version_b.connections}

    nodes_added = [nodes_b[k] for k in nodes_b if k not in nodes_a]
    nodes_removed = [nodes_a[k] for k in nodes_a if k not in nodes_b]

    nodes_modified: list[dict[str, Any]] = []
    for k, node_a in nodes_a.items():
        if k in nodes_b and nodes_b[k] != node_a:
            nodes_modified.append(
                {"nodeId": k, "changes": _deep_diff(node_a, nodes_b[k])}
            )

    connections_added = [conn_b[k] for k in conn_b if k not in conn_a]
    connections_removed = [conn_a[k] for k in conn_a if k not in conn_b]

    return {
        "nodesAdded": nodes_added,
        "nodesRemoved": nodes_removed,
        "nodesModified": nodes_modified,
        "connectionsAdded": connections_added,
        "connectionsRemoved": connections_removed,
    }


def _deep_diff(a: Any, b: Any, path: str = "") -> dict[str, Any]:
    """Compute a deep diff between two JSON-serializable values."""
    diff: dict[str, Any] = {}
    if isinstance(a, dict) and isinstance(b, dict):
        all_keys = set(a.keys()) | set(b.keys())
        for key in all_keys:
            child_path = f"{path}.{key}" if path else key
            if key not in a:
                diff[child_path] = {"added": b[key]}
            elif key not in b:
                diff[child_path] = {"removed": a[key]}
            elif a[key] != b[key]:
                if isinstance(a[key], (dict, list)) and isinstance(b[key], (dict, list)):
                    nested = _deep_diff(a[key], b[key], child_path)
                    diff.update(nested)
                else:
                    diff[child_path] = {"from": a[key], "to": b[key]}
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b) or any(x != y for x, y in zip(a, b)):
            diff[path or "root"] = {"from": a, "to": b}
    elif a != b:
        diff[path or "root"] = {"from": a, "to": b}
    return diff
