"""Node and edge management views."""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.workflows_v2.models.edge import WorkflowEdge
from apps.workflows_v2.models.node import WorkflowNode
from apps.workflows_v2.models.workflow import Workflow
from apps.workflows_v2.serializers import (
    EdgeCreateSchema,
    EdgeOutSchema,
    EdgeUpdateSchema,
    ErrorSchema,
    NodeCreateSchema,
    NodeOutSchema,
    NodeUpdateSchema,
)
from apps.workflows_v2.services.builder import (
    create_edge,
    create_node,
    delete_edge,
    delete_node,
    update_edge,
    update_node,
)

router = Router(auth=VoyagerKeycloakBearer())


def _get_tenant(request) -> str:
    """Extract tenant_id from request."""
    return getattr(request, "tenant_id", "") or getattr(request.auth, "tenant_id", "default")


@router.get("/{workflow_id}/nodes", response=list[NodeOutSchema], tags=["Workflow Nodes"])
def list_nodes(request, workflow_id: int) -> list[WorkflowNode]:
    """List all nodes in a workflow."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    return list(workflow.workflow_nodes.all())


@router.post("/{workflow_id}/nodes", response=NodeOutSchema, tags=["Workflow Nodes"])
def add_node(request, workflow_id: int, payload: NodeCreateSchema) -> WorkflowNode:
    """Add a node to a workflow."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    return create_node(
        workflow=workflow,
        node_id=payload.node_id,
        node_type=payload.node_type,
        label=payload.label,
        config=payload.config,
        position=payload.position,
    )


@router.put("/{workflow_id}/nodes/{node_db_id}", response=NodeOutSchema, tags=["Workflow Nodes"])
def update_node_view(
    request,
    workflow_id: int,
    node_db_id: int,
    payload: NodeUpdateSchema,
) -> WorkflowNode:
    """Update a node."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    node = get_object_or_404(WorkflowNode, id=node_db_id, workflow=workflow)
    return update_node(
        node=node,
        label=payload.label,
        config=payload.config,
        position=payload.position,
    )


@router.delete(
    "/{workflow_id}/nodes/{node_db_id}",
    response={200: dict, 404: ErrorSchema},
    tags=["Workflow Nodes"],
)
def remove_node(request, workflow_id: int, node_db_id: int) -> dict[str, Any]:
    """Delete a node and its connected edges."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    node = get_object_or_404(WorkflowNode, id=node_db_id, workflow=workflow)
    delete_node(node)
    return {"status": "deleted", "node_id": node.node_id}


@router.get("/{workflow_id}/edges", response=list[EdgeOutSchema], tags=["Workflow Edges"])
def list_edges(request, workflow_id: int) -> list[WorkflowEdge]:
    """List all edges in a workflow."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    return list(workflow.workflow_edges.all())


@router.post("/{workflow_id}/edges", response=EdgeOutSchema, tags=["Workflow Edges"])
def add_edge(request, workflow_id: int, payload: EdgeCreateSchema) -> WorkflowEdge:
    """Add an edge to a workflow."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    return create_edge(
        workflow=workflow,
        source=payload.source,
        target=payload.target,
        label=payload.label,
        condition=payload.condition,
    )


@router.put("/{workflow_id}/edges/{edge_db_id}", response=EdgeOutSchema, tags=["Workflow Edges"])
def update_edge_view(
    request,
    workflow_id: int,
    edge_db_id: int,
    payload: EdgeUpdateSchema,
) -> WorkflowEdge:
    """Update an edge."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    edge = get_object_or_404(WorkflowEdge, id=edge_db_id, workflow=workflow)
    return update_edge(
        edge=edge,
        label=payload.label,
        condition=payload.condition,
    )


@router.delete(
    "/{workflow_id}/edges/{edge_db_id}",
    response={200: dict, 404: ErrorSchema},
    tags=["Workflow Edges"],
)
def remove_edge(request, workflow_id: int, edge_db_id: int) -> dict[str, Any]:
    """Delete an edge."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    edge = get_object_or_404(WorkflowEdge, id=edge_db_id, workflow=workflow)
    delete_edge(edge)
    return {"status": "deleted", "source": edge.source, "target": edge.target}
