"""API tests for Workflows v2 endpoints.

Tests workflows, nodes, executions under ``/api/v1/workflows/``.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.workflows_v2.models.workflow import Workflow
from apps.workflows_v2.models.node import WorkflowNode
from apps.workflows_v2.models.execution import WorkflowExecution

client = Client()


@pytest.fixture
def workflow(tenant_id: str) -> Workflow:
    """Create a test workflow."""
    return Workflow.objects.create(
        tenant_id=tenant_id,
        name="Test Workflow",
        description="A workflow for API testing",
        status="draft",
        trigger_type="manual",
    )


@pytest.fixture
def workflow_node(tenant_id: str, workflow: Workflow) -> WorkflowNode:
    """Create a test workflow node."""
    return WorkflowNode.objects.create(
        workflow=workflow,
        node_type="action",
        name="Send Email",
        config={"template": "welcome"},
        position_x=100,
        position_y=200,
    )


@pytest.fixture
def execution(tenant_id: str, workflow: Workflow) -> WorkflowExecution:
    """Create a test workflow execution."""
    return WorkflowExecution.objects.create(
        tenant_id=tenant_id,
        workflow=workflow,
        status="running",
        triggered_by="user-001",
    )


@pytest.mark.django_db
def test_workflows_health_requires_auth() -> None:
    """GET /workflows/health without auth returns 401."""
    response = client.get("/api/v1/workflows/health")
    assert response.status_code == 401


@pytest.mark.django_db
def test_workflows_health(auth_headers: dict[str, str]) -> None:
    """GET /workflows/health returns module health."""
    response = client.get("/api/v1/workflows/health", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["module"] == "workflows_v2"


@pytest.mark.django_db
def test_list_workflows(auth_headers: dict[str, str], workflow: Workflow) -> None:
    """GET /workflows/workflows returns workflows."""
    response = client.get("/api/v1/workflows/workflows", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_workflow(auth_headers: dict[str, str]) -> None:
    """POST /workflows/workflows creates a workflow."""
    payload = {
        "name": "API Workflow",
        "description": "Created via API",
        "status": "draft",
        "trigger_type": "scheduled",
    }
    response = client.post(
        "/api/v1/workflows/workflows",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "API Workflow"


@pytest.mark.django_db
def test_get_workflow(auth_headers: dict[str, str], workflow: Workflow) -> None:
    """GET /workflows/workflows/{id} returns a workflow."""
    response = client.get(f"/api/v1/workflows/workflows/{workflow.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Workflow"


@pytest.mark.django_db
def test_update_workflow(auth_headers: dict[str, str], workflow: Workflow) -> None:
    """PUT /workflows/workflows/{id} updates a workflow."""
    payload = {"name": "Updated Workflow", "status": "active"}
    response = client.put(
        f"/api/v1/workflows/workflows/{workflow.id}",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Workflow"


@pytest.mark.django_db
def test_delete_workflow(auth_headers: dict[str, str], workflow: Workflow) -> None:
    """DELETE /workflows/workflows/{id} removes a workflow."""
    response = client.delete(f"/api/v1/workflows/workflows/{workflow.id}", **auth_headers)
    assert response.status_code == 200
    assert not Workflow.objects.filter(id=workflow.id).exists()


@pytest.mark.django_db
def test_list_nodes(auth_headers: dict[str, str], workflow_node: WorkflowNode) -> None:
    """GET /workflows/workflows/{id}/nodes returns nodes."""
    response = client.get(
        f"/api/v1/workflows/workflows/{workflow_node.workflow.id}/nodes", **auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_node(auth_headers: dict[str, str], workflow: Workflow) -> None:
    """POST /workflows/workflows/{id}/nodes creates a node."""
    payload = {
        "node_type": "trigger",
        "name": "Start Node",
        "config": {},
        "position_x": 50,
        "position_y": 50,
    }
    response = client.post(
        f"/api/v1/workflows/workflows/{workflow.id}/nodes",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Start Node"


@pytest.mark.django_db
def test_list_executions(auth_headers: dict[str, str], execution: WorkflowExecution) -> None:
    """GET /workflows/workflows/{id}/executions returns executions."""
    response = client.get(
        f"/api/v1/workflows/workflows/{execution.workflow.id}/executions", **auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
