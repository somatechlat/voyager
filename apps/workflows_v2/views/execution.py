"""Execution monitoring views."""

from __future__ import annotations

import asyncio
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.workflows_v2.models.workflow import Workflow
from apps.workflows_v2.models.execution import WorkflowExecution
from apps.workflows_v2.serializers import (
    ExecutionOutSchema,
    ExecutionStartSchema,
    ExecutionProgressSchema,
    ErrorSchema,
)
from apps.workflows_v2.services.execution import (
    start_execution,
    cancel_execution,
    get_execution_progress,
)
from apps.workflows_v2.services.vortex_integration import (
    submit_workflow_to_vortex,
    execute_on_vortex,
    get_execution_status,
    cancel_vortex_execution,
    sync_execution_status,
)

router = Router(auth=VoyagerKeycloakBearer())


def _get_tenant(request) -> str:
    """Extract tenant_id from request."""
    return getattr(request, "tenant_id", "") or getattr(request.auth, "tenant_id", "default")


def _get_token(request) -> str:
    """Extract JWT token from request."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return ""


@router.get(
    "/{workflow_id}/executions",
    response=list[ExecutionOutSchema],
    tags=["Executions"],
)
def list_executions(
    request,
    workflow_id: int,
    status: str | None = None,
) -> list[WorkflowExecution]:
    """List executions for a workflow."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    qs = workflow.executions.order_by("-started_at")
    if status:
        qs = qs.filter(status=status)
    return list(qs)


@router.post(
    "/{workflow_id}/executions",
    response=ExecutionOutSchema,
    tags=["Executions"],
)
def create_execution(
    request,
    workflow_id: int,
    payload: ExecutionStartSchema,
) -> WorkflowExecution:
    """Start a new workflow execution."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    return start_execution(
        workflow=workflow,
        trigger_type="manual",
        trigger_data=payload.trigger_data,
        user_id=getattr(request.auth, "sub", None),
    )


@router.get(
    "/{workflow_id}/executions/{execution_id}",
    response=ExecutionOutSchema,
    tags=["Executions"],
)
def get_execution(
    request, workflow_id: int, execution_id: int
) -> WorkflowExecution:
    """Get a single execution."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    return get_object_or_404(WorkflowExecution, id=execution_id, workflow=workflow)


@router.get(
    "/{workflow_id}/executions/{execution_id}/progress",
    response=ExecutionProgressSchema,
    tags=["Executions"],
)
def execution_progress(
    request, workflow_id: int, execution_id: int
) -> dict[str, Any]:
    """Get execution progress."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    execution = get_object_or_404(
        WorkflowExecution, id=execution_id, workflow=workflow
    )
    return get_execution_progress(execution)


@router.post(
    "/{workflow_id}/executions/{execution_id}/cancel",
    response={200: dict, 404: ErrorSchema},
    tags=["Executions"],
)
def cancel_execution_view(
    request, workflow_id: int, execution_id: int
) -> dict[str, Any]:
    """Cancel a running execution."""
    tenant_id = _get_tenant(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    execution = get_object_or_404(
        WorkflowExecution, id=execution_id, workflow=workflow
    )
    cancel_execution(execution)

    # Also cancel on Vortex if applicable
    token = _get_token(request)
    if execution.run_id and token:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                cancel_vortex_execution(execution.run_id, token)
            )
            loop.close()
            return {"status": "cancelled", "vortex_cancelled": result}
        except Exception:
            pass

    return {"status": "cancelled"}


@router.post(
    "/{workflow_id}/executions/{execution_id}/vortex-submit",
    response=dict,
    tags=["Executions"],
)
def submit_to_vortex(
    request, workflow_id: int, execution_id: int
) -> dict[str, Any]:
    """Submit a workflow to Vortex for execution."""
    tenant_id = _get_tenant(request)
    token = _get_token(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    execution = get_object_or_404(
        WorkflowExecution, id=execution_id, workflow=workflow
    )

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        graph_id = loop.run_until_complete(
            submit_workflow_to_vortex(workflow, token)
        )
        run_id = loop.run_until_complete(
            execute_on_vortex(graph_id, token, execution)
        )
        loop.close()
        return {
            "status": "submitted",
            "graph_id": graph_id,
            "run_id": run_id,
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


@router.get(
    "/{workflow_id}/executions/{execution_id}/vortex-status",
    response=dict,
    tags=["Executions"],
)
def vortex_status(request, workflow_id: int, execution_id: int) -> dict[str, Any]:
    """Get Vortex execution status."""
    tenant_id = _get_tenant(request)
    token = _get_token(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    execution = get_object_or_404(
        WorkflowExecution, id=execution_id, workflow=workflow
    )

    if not execution.run_id:
        return {"error": "No Vortex run associated"}

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        status = loop.run_until_complete(
            get_execution_status(execution.run_id, token)
        )
        loop.close()
        return status
    except Exception as exc:
        return {"error": str(exc)}


@router.post(
    "/{workflow_id}/executions/{execution_id}/sync",
    response=dict,
    tags=["Executions"],
)
def sync_status(request, workflow_id: int, execution_id: int) -> dict[str, Any]:
    """Synchronize execution status with Vortex."""
    tenant_id = _get_tenant(request)
    token = _get_token(request)
    workflow = get_object_or_404(Workflow, id=workflow_id, tenant_id=tenant_id)
    execution = get_object_or_404(
        WorkflowExecution, id=execution_id, workflow=workflow
    )

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            sync_execution_status(execution, token)
        )
        loop.close()
        return result
    except Exception as exc:
        return {"error": str(exc)}
