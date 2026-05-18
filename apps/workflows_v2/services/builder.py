"""Workflow builder service — node/edge CRUD and JSON sync.

Provides create, update, and delete operations for workflow nodes
and edges, with automatic JSON field synchronization.
"""

from __future__ import annotations

from typing import Any

from django.db import models as django_models

from apps.workflows_v2.models.workflow import Workflow
from apps.workflows_v2.models.node import WorkflowNode
from apps.workflows_v2.models.edge import WorkflowEdge


models_q = django_models.Q


def create_node(
    workflow: Workflow,
    node_id: str,
    node_type: str,
    label: str,
    config: dict[str, Any],
    position: dict[str, int],
) -> WorkflowNode:
    """Create a new node in a workflow.

    Args:
        workflow: The parent workflow.
        node_id: Client-generated unique identifier.
        node_type: One of the 10 node types.
        label: Human-readable label.
        config: Node-specific configuration.
        position: Visual position {x, y}.

    Returns:
        The created WorkflowNode instance.
    """
    node = WorkflowNode.objects.create(
        workflow=workflow,
        node_id=node_id,
        node_type=node_type,
        label=label,
        config=config,
        position=position,
    )
    _sync_nodes_to_json(workflow)
    return node


def update_node(
    node: WorkflowNode,
    label: str | None = None,
    config: dict[str, Any] | None = None,
    position: dict[str, int] | None = None,
) -> WorkflowNode:
    """Update an existing node's properties.

    Args:
        node: The node to update.
        label: New label (optional).
        config: New config (optional).
        position: New position (optional).

    Returns:
        The updated WorkflowNode instance.
    """
    if label is not None:
        node.label = label
    if config is not None:
        node.config = config
    if position is not None:
        node.position = position
    node.save(update_fields=["label", "config", "position", "updated_at"])
    _sync_nodes_to_json(node.workflow)
    return node


def delete_node(node: WorkflowNode) -> None:
    """Delete a node and all its connected edges.

    Args:
        node: The node to delete.
    """
    workflow = node.workflow
    WorkflowEdge.objects.filter(
        django_models.Q(source=node.node_id) | django_models.Q(target=node.node_id),
        workflow=workflow,
    ).delete()
    node.delete()
    _sync_nodes_to_json(workflow)
    _sync_edges_to_json(workflow)


def create_edge(
    workflow: Workflow,
    source: str,
    target: str,
    label: str = "",
    condition: str = "",
) -> WorkflowEdge:
    """Create a new edge between two nodes.

    Args:
        workflow: The parent workflow.
        source: Source node_id.
        target: Target node_id.
        label: Optional edge label.
        condition: Optional conditional expression.

    Returns:
        The created WorkflowEdge instance.
    """
    edge = WorkflowEdge.objects.create(
        workflow=workflow,
        source=source,
        target=target,
        label=label,
        condition=condition,
    )
    _sync_edges_to_json(workflow)
    return edge


def update_edge(
    edge: WorkflowEdge,
    label: str | None = None,
    condition: str | None = None,
) -> WorkflowEdge:
    """Update an existing edge.

    Args:
        edge: The edge to update.
        label: New label (optional).
        condition: New condition (optional).

    Returns:
        The updated WorkflowEdge instance.
    """
    if label is not None:
        edge.label = label
    if condition is not None:
        edge.condition = condition
    edge.save(update_fields=["label", "condition"])
    _sync_edges_to_json(edge.workflow)
    return edge


def delete_edge(edge: WorkflowEdge) -> None:
    """Delete an edge.

    Args:
        edge: The edge to delete.
    """
    workflow = edge.workflow
    edge.delete()
    _sync_edges_to_json(workflow)


def _sync_nodes_to_json(workflow: Workflow) -> None:
    """Sync all nodes back to the workflow's nodes JSON field."""
    nodes = list(
        workflow.workflow_nodes.values(
            "node_id", "node_type", "label", "config", "position"
        )
    )
    workflow.nodes = nodes
    workflow.save(update_fields=["nodes", "updated_at"])


def _sync_edges_to_json(workflow: Workflow) -> None:
    """Sync all edges back to the workflow's connections JSON field."""
    edges = list(
        workflow.workflow_edges.values("source", "target", "label", "condition")
    )
    workflow.connections = edges
    workflow.save(update_fields=["connections", "updated_at"])


# Re-export from validation module for backward compatibility
from apps.workflows_v2.services.validation import (  # noqa: E402
    validate_workflow,
    simulate_workflow,
    publish_version,
    compare_versions,
)
