"""Workspace CRUD endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from django.http import HttpRequest
from ninja import Query
from ninja.errors import HttpError

from apps.rbac.serializers import (
    WorkspaceCreateSchema,
    WorkspaceDetailResponse,
    WorkspaceListResponse,
    WorkspaceSchema,
    WorkspaceUpdateSchema,
)

from .stores import (
    _assignments_db,
    _audit_log,
    _workspaces_db,
    get_user,
)


def list_workspaces(
    request: HttpRequest,
    tenant_id: str | None = Query(None, description="Filter by tenant"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> WorkspaceListResponse:
    """List workspaces with optional filtering.

    Args:
        request: HTTP request.
        tenant_id: Filter by tenant.
        is_active: Filter by active status.
        page: Page number.
        page_size: Items per page.

    Returns:
        Paginated workspace list.
    """
    user = get_user(request)
    if not user.has_permission("voyager:read:*"):
        raise HttpError(403, "Permission denied")

    all_workspaces = list(_workspaces_db.values())

    # Non-superadmins only see their tenant's workspaces
    if not user.is_superadmin():
        all_workspaces = [w for w in all_workspaces if w["tenant_id"] == user.tenant_id]

    if tenant_id:
        all_workspaces = [w for w in all_workspaces if w["tenant_id"] == tenant_id]
    if is_active is not None:
        all_workspaces = [w for w in all_workspaces if w["is_active"] == is_active]

    total = len(all_workspaces)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = all_workspaces[start:end]

    items = [
        WorkspaceSchema(
            id=w["id"],
            name=w["name"],
            slug=w["slug"],
            tenant_id=w["tenant_id"],
            description=w["description"],
            is_active=w["is_active"],
            created_at=w["created_at"],
            updated_at=w["updated_at"],
        )
        for w in page_items
    ]

    return WorkspaceListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


def create_workspace(
    request: HttpRequest,
    payload: WorkspaceCreateSchema,
) -> WorkspaceSchema:
    """Create a new workspace.

    Args:
        request: HTTP request.
        payload: Workspace creation data.

    Returns:
        The newly created workspace.

    Raises:
        HttpError: 403 if user lacks workspace creation permission.
    """
    user = get_user(request)
    if not (user.is_tenant_admin() or user.has_permission("voyager:manage:workspace")):
        raise HttpError(403, "Access denied: tenant admin or workspace manager required")

    for existing in _workspaces_db.values():
        if existing["slug"] == payload.slug:
            raise HttpError(400, f"Workspace slug '{payload.slug}' already exists")

    ws_id = uuid4()
    now = datetime.utcnow()
    ws_data = {
        "id": ws_id,
        "name": payload.name,
        "slug": payload.slug,
        "tenant_id": payload.tenant_id,
        "description": payload.description,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    _workspaces_db[str(ws_id)] = ws_data

    _audit_log(
        "workspace.created",
        user,
        payload.name,
        workspace_id=str(ws_id),
        details={"slug": payload.slug, "tenant_id": payload.tenant_id},
    )

    return WorkspaceSchema(
        id=ws_id,
        name=payload.name,
        slug=payload.slug,
        tenant_id=payload.tenant_id,
        description=payload.description,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def get_workspace(
    request: HttpRequest,
    workspace_id: UUID,
) -> WorkspaceDetailResponse:
    """Get workspace details with member list.

    Args:
        request: HTTP request.
        workspace_id: UUID of the workspace.

    Returns:
        Workspace details with members.

    Raises:
        HttpError: 404 if workspace not found.
    """
    user = get_user(request)
    ws_data = _workspaces_db.get(str(workspace_id))
    if not ws_data:
        raise HttpError(404, f"Workspace {workspace_id} not found")

    if not user.is_superadmin() and ws_data["tenant_id"] != user.tenant_id:
        raise HttpError(403, "Access denied: cross-tenant workspace access")

    ws = WorkspaceSchema(
        id=ws_data["id"],
        name=ws_data["name"],
        slug=ws_data["slug"],
        tenant_id=ws_data["tenant_id"],
        description=ws_data["description"],
        is_active=ws_data["is_active"],
        created_at=ws_data["created_at"],
        updated_at=ws_data["updated_at"],
    )

    # Find members via role assignments scoped to this workspace
    members = []
    for a in _assignments_db.values():
        if a.get("workspace_id") == str(workspace_id):
            members.append(
                {
                    "user_id": a["user_id"],
                    "username": a["user_id"][:8],  # placeholder
                    "email": "",
                    "roles": ["assigned"],
                    "joined_at": a["granted_at"],
                }
            )

    from apps.rbac.serializers import WorkspaceMemberSchema

    member_items = [
        WorkspaceMemberSchema(
            user_id=m["user_id"],
            username=m["username"],
            email=m["email"],
            roles=m["roles"],
            joined_at=m["joined_at"],
        )
        for m in members
    ]

    return WorkspaceDetailResponse(
        workspace=ws,
        members=member_items,
        member_count=len(member_items),
    )


def update_workspace(
    request: HttpRequest,
    workspace_id: UUID,
    payload: WorkspaceUpdateSchema,
) -> WorkspaceSchema:
    """Update an existing workspace.

    Args:
        request: HTTP request.
        workspace_id: UUID of the workspace.
        payload: Update data.

    Returns:
        Updated workspace.

    Raises:
        HttpError: 404 if workspace not found.
        HttpError: 403 if user lacks permission.
    """
    user = get_user(request)
    if not user.is_workspace_admin(str(workspace_id)):
        raise HttpError(403, "Access denied: workspace admin required")

    ws_data = _workspaces_db.get(str(workspace_id))
    if not ws_data:
        raise HttpError(404, f"Workspace {workspace_id} not found")

    if payload.name is not None:
        ws_data["name"] = payload.name
    if payload.description is not None:
        ws_data["description"] = payload.description
    if payload.is_active is not None:
        ws_data["is_active"] = payload.is_active

    ws_data["updated_at"] = datetime.utcnow()

    return WorkspaceSchema(
        id=ws_data["id"],
        name=ws_data["name"],
        slug=ws_data["slug"],
        tenant_id=ws_data["tenant_id"],
        description=ws_data["description"],
        is_active=ws_data["is_active"],
        created_at=ws_data["created_at"],
        updated_at=ws_data["updated_at"],
    )


def delete_workspace(
    request: HttpRequest,
    workspace_id: UUID,
) -> dict[str, str]:
    """Soft-delete a workspace by setting is_active=False.

    Args:
        request: HTTP request.
        workspace_id: UUID of the workspace.

    Returns:
        Success confirmation.

    Raises:
        HttpError: 404 if workspace not found.
        HttpError: 403 if user lacks permission.
    """
    user = get_user(request)
    if not user.is_tenant_admin():
        raise HttpError(403, "Access denied: tenant admin required")

    ws_data = _workspaces_db.get(str(workspace_id))
    if not ws_data:
        raise HttpError(404, f"Workspace {workspace_id} not found")

    ws_data["is_active"] = False
    ws_data["updated_at"] = datetime.utcnow()

    _audit_log(
        "workspace.deactivated",
        user,
        ws_data["name"],
        workspace_id=str(workspace_id),
    )

    return {"status": "deactivated", "workspace_id": str(workspace_id)}
