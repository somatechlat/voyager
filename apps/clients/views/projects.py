"""Project and milestone API endpoints."""

from __future__ import annotations

from ninja import Router
from ninja.errors import HttpError

from apps.clients.models.project import ProjectMilestone
from apps.clients.serializers import (
    MilestoneCreateSchema,
    MilestoneSchema,
    MilestoneUpdateSchema,
    PaginatedMilestonesSchema,
    PaginatedProjectsSchema,
    ProjectCreateSchema,
    ProjectDetailSchema,
    ProjectListSchema,
    ProjectUpdateSchema,
)
from apps.clients.services import ProjectService
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


def _get_tenant(request) -> str:
    """Extract tenant_id from the authenticated user."""
    return getattr(request.auth, "tenant_id", "default")


# ============================================================================
# Project CRUD
# ============================================================================


@router.get("/projects", response=PaginatedProjectsSchema, tags=["Projects"])
def list_projects(
    request,
    client_id: int | None = None,
    status: str | None = None,
    manager_id: str | None = None,
):
    """List all projects for the current tenant."""
    tenant_id = _get_tenant(request)
    qs = ProjectService.list_projects(tenant_id, client_id, status, manager_id)
    items = list(qs[:100])
    return PaginatedProjectsSchema(
        count=qs.count(),
        items=[
            ProjectListSchema(
                id=p.id,
                name=p.name,
                status=p.status,
                budget_type=p.budget_type,
                start_date=p.start_date,
                end_date=p.end_date,
                manager_id=p.manager_id,
                created_at=p.created_at,
            )
            for p in items
        ],
    )


@router.get(
    "/clients/{client_id}/projects", response=PaginatedProjectsSchema, tags=["Projects"]
)
def list_client_projects(request, client_id: int, status: str | None = None):
    """List all projects for a specific client."""
    tenant_id = _get_tenant(request)
    qs = ProjectService.list_projects(tenant_id, client_id, status)
    items = list(qs[:100])
    return PaginatedProjectsSchema(
        count=qs.count(),
        items=[
            ProjectListSchema(
                id=p.id,
                name=p.name,
                status=p.status,
                budget_type=p.budget_type,
                start_date=p.start_date,
                end_date=p.end_date,
                manager_id=p.manager_id,
                created_at=p.created_at,
            )
            for p in items
        ],
    )


@router.post(
    "/clients/{client_id}/projects",
    response=ProjectDetailSchema,
    tags=["Projects"],
)
def create_project(request, client_id: int, payload: ProjectCreateSchema):
    """Create a new project for a client."""
    tenant_id = _get_tenant(request)
    data = payload.dict()
    return ProjectService.create(tenant_id, client_id, data)


@router.get("/projects/{project_id}", response=ProjectDetailSchema, tags=["Projects"])
def get_project(request, project_id: int):
    """Retrieve a single project by ID."""
    tenant_id = _get_tenant(request)
    return ProjectService.get_by_id(tenant_id, project_id)


@router.put("/projects/{project_id}", response=ProjectDetailSchema, tags=["Projects"])
def update_project(request, project_id: int, payload: ProjectUpdateSchema):
    """Update an existing project."""
    tenant_id = _get_tenant(request)
    project = ProjectService.get_by_id(tenant_id, project_id)
    data = {k: v for k, v in payload.dict().items() if v is not None}
    return ProjectService.update(project, data)


@router.delete("/projects/{project_id}", tags=["Projects"])
def delete_project(request, project_id: int):
    """Delete a project."""
    tenant_id = _get_tenant(request)
    project = ProjectService.get_by_id(tenant_id, project_id)
    ProjectService.delete(project)
    return {"success": True, "message": f"Project {project_id} deleted"}


# ============================================================================
# Milestone endpoints
# ============================================================================


@router.get(
    "/projects/{project_id}/milestones",
    response=PaginatedMilestonesSchema,
    tags=["Projects"],
)
def list_milestones(request, project_id: int):
    """List all milestones for a project."""
    tenant_id = _get_tenant(request)
    ProjectService.get_by_id(tenant_id, project_id)
    qs = ProjectService.list_milestones(project_id)
    items = list(qs[:100])
    return PaginatedMilestonesSchema(
        count=qs.count(),
        items=[
            MilestoneSchema(
                id=m.id,
                project_id=m.project_id,
                name=m.name,
                description=m.description,
                due_date=m.due_date,
                status=m.status,
                deliverables=m.deliverables,
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
            for m in items
        ],
    )


@router.post(
    "/projects/{project_id}/milestones",
    response=MilestoneSchema,
    tags=["Projects"],
)
def create_milestone(request, project_id: int, payload: MilestoneCreateSchema):
    """Create a milestone for a project."""
    tenant_id = _get_tenant(request)
    ProjectService.get_by_id(tenant_id, project_id)
    data = payload.dict()
    milestone = ProjectService.create_milestone(project_id, data)
    return MilestoneSchema(
        id=milestone.id,
        project_id=milestone.project_id,
        name=milestone.name,
        description=milestone.description,
        due_date=milestone.due_date,
        status=milestone.status,
        deliverables=milestone.deliverables,
        created_at=milestone.created_at,
        updated_at=milestone.updated_at,
    )


@router.get(
    "/projects/{project_id}/milestones/{milestone_id}",
    response=MilestoneSchema,
    tags=["Projects"],
)
def get_milestone(request, project_id: int, milestone_id: int):
    """Retrieve a single milestone."""
    milestone = ProjectService.get_milestone_by_id(project_id, milestone_id)
    return MilestoneSchema(
        id=milestone.id,
        project_id=milestone.project_id,
        name=milestone.name,
        description=milestone.description,
        due_date=milestone.due_date,
        status=milestone.status,
        deliverables=milestone.deliverables,
        created_at=milestone.created_at,
        updated_at=milestone.updated_at,
    )


@router.put(
    "/projects/{project_id}/milestones/{milestone_id}",
    response=MilestoneSchema,
    tags=["Projects"],
)
def update_milestone(
    request, project_id: int, milestone_id: int, payload: MilestoneUpdateSchema
):
    """Update a milestone."""
    milestone = ProjectService.get_milestone_by_id(project_id, milestone_id)
    data = {k: v for k, v in payload.dict().items() if v is not None}
    updated = ProjectService.update_milestone(milestone, data)
    return MilestoneSchema(
        id=updated.id,
        project_id=updated.project_id,
        name=updated.name,
        description=updated.description,
        due_date=updated.due_date,
        status=updated.status,
        deliverables=updated.deliverables,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.delete(
    "/projects/{project_id}/milestones/{milestone_id}",
    tags=["Projects"],
)
def delete_milestone(request, project_id: int, milestone_id: int):
    """Delete a milestone."""
    milestone = ProjectService.get_milestone_by_id(project_id, milestone_id)
    ProjectService.delete_milestone(milestone)
    return {"success": True, "message": f"Milestone {milestone_id} deleted"}


@router.get("/projects/{project_id}/timeline", tags=["Projects"])
def get_project_timeline(request, project_id: int):
    """Get timeline summary for a project."""
    tenant_id = _get_tenant(request)
    ProjectService.get_by_id(tenant_id, project_id)
    return ProjectService.get_timeline(project_id)
