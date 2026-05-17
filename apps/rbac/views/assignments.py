"""Role assignment endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from django.http import HttpRequest
from ninja import Query
from ninja.errors import HttpError

from apps.rbac.serializers import (
    RoleAssignmentCreateSchema,
    RoleAssignmentListResponse,
    RoleAssignmentRevokeSchema,
    RoleAssignmentSchema,
    RoleSchema,
    UserPermissionsResponse,
    UserRolesResponse,
)

from .stores import (
    _assignments_db,
    _audit_log,
    _roles_db,
    get_user,
)


def list_role_assignments(
    request: HttpRequest,
    user_id: str | None = Query(None, description="Filter by user"),
    role_id: UUID | None = Query(None, description="Filter by role"),
    tenant_id: str | None = Query(None, description="Filter by tenant"),
    workspace_id: str | None = Query(None, description="Filter by workspace"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> RoleAssignmentListResponse:
    """List role assignments with optional filtering.

    Args:
        request: HTTP request.
        user_id: Filter by assigned user's Keycloak sub.
        role_id: Filter by role UUID.
        tenant_id: Filter by tenant.
        workspace_id: Filter by workspace.
        page: Page number.
        page_size: Items per page.

    Returns:
        Paginated assignment list.
    """
    user = get_user(request)
    if not user.has_permission("voyager:read:*"):
        raise HttpError(403, "Permission denied")

    all_assignments = list(_assignments_db.values())

    if user_id:
        all_assignments = [a for a in all_assignments if a["user_id"] == user_id]
    if role_id:
        all_assignments = [a for a in all_assignments if str(a.get("role_id")) == str(role_id)]
    if tenant_id:
        all_assignments = [a for a in all_assignments if a["tenant_id"] == tenant_id]
    if workspace_id:
        all_assignments = [a for a in all_assignments if a.get("workspace_id") == workspace_id]

    total = len(all_assignments)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = all_assignments[start:end]

    items = []
    for a in page_items:
        role_data = _roles_db.get(str(a["role_id"]), {})
        role_schema = RoleSchema(
            id=role_data.get("id", a["role_id"]),
            name=role_data.get("name", "unknown"),
            description=role_data.get("description", ""),
            parent_id=role_data.get("parent_id"),
            permissions=role_data.get("permissions", []),
            is_system=role_data.get("is_system", False),
            created_at=role_data.get("created_at", datetime.utcnow()),
            updated_at=role_data.get("updated_at", datetime.utcnow()),
        )
        items.append(
            RoleAssignmentSchema(
                id=a["id"],
                user_id=a["user_id"],
                role=role_schema,
                tenant_id=a["tenant_id"],
                workspace_id=a.get("workspace_id"),
                granted_by=a["granted_by"],
                granted_at=a["granted_at"],
                expires_at=a.get("expires_at"),
            )
        )

    return RoleAssignmentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


def assign_role(
    request: HttpRequest,
    payload: RoleAssignmentCreateSchema,
) -> RoleAssignmentSchema:
    """Assign a role to a user.

    Args:
        request: HTTP request.
        payload: Assignment data including user_id, role_id, and scope.

    Returns:
        The created assignment record.

    Raises:
        HttpError: 403 if user lacks tenant-admin role.
        HttpError: 404 if role not found.
        HttpError: 400 if assignment already exists.
    """
    user = get_user(request)
    if not user.is_tenant_admin():
        raise HttpError(403, "Access denied: tenant admin required")

    role_data = _roles_db.get(str(payload.role_id))
    if not role_data:
        raise HttpError(404, f"Role {payload.role_id} not found")

    # Check for duplicate
    for a in _assignments_db.values():
        if (
            a["user_id"] == payload.user_id
            and str(a.get("role_id")) == str(payload.role_id)
            and a["tenant_id"] == payload.tenant_id
            and a.get("workspace_id") == payload.workspace_id
        ):
            raise HttpError(400, "Role assignment already exists")

    assignment_id = uuid4()
    now = datetime.utcnow()
    assignment_data = {
        "id": assignment_id,
        "user_id": payload.user_id,
        "role_id": payload.role_id,
        "tenant_id": payload.tenant_id,
        "workspace_id": payload.workspace_id,
        "granted_by": user.user_id,
        "granted_at": now,
        "expires_at": payload.expires_at,
    }
    _assignments_db[str(assignment_id)] = assignment_data

    _audit_log(
        "role.assigned",
        user,
        role_data["name"],
        target_user_id=payload.user_id,
        workspace_id=payload.workspace_id,
    )

    role_schema = RoleSchema(
        id=role_data["id"],
        name=role_data["name"],
        description=role_data["description"],
        parent_id=role_data.get("parent_id"),
        permissions=role_data["permissions"],
        is_system=role_data["is_system"],
        created_at=role_data["created_at"],
        updated_at=role_data["updated_at"],
    )

    return RoleAssignmentSchema(
        id=assignment_id,
        user_id=payload.user_id,
        role=role_schema,
        tenant_id=payload.tenant_id,
        workspace_id=payload.workspace_id,
        granted_by=user.user_id,
        granted_at=now,
        expires_at=payload.expires_at,
    )


def revoke_role_assignment(
    request: HttpRequest,
    assignment_id: UUID,
    payload: RoleAssignmentRevokeSchema | None = None,
) -> dict[str, str]:
    """Revoke a role assignment.

    Args:
        request: HTTP request.
        assignment_id: UUID of the assignment to revoke.
        payload: Optional revocation reason.

    Returns:
        Success confirmation.

    Raises:
        HttpError: 403 if user lacks tenant-admin role.
        HttpError: 404 if assignment not found.
    """
    user = get_user(request)
    if not user.is_tenant_admin():
        raise HttpError(403, "Access denied: tenant admin required")

    assignment_data = _assignments_db.get(str(assignment_id))
    if not assignment_data:
        raise HttpError(404, f"Assignment {assignment_id} not found")

    role_data = _roles_db.get(str(assignment_data.get("role_id", "")), {})
    role_name = role_data.get("name", "unknown")

    del _assignments_db[str(assignment_id)]

    _audit_log(
        "role.revoked",
        user,
        role_name,
        target_user_id=assignment_data["user_id"],
        workspace_id=assignment_data.get("workspace_id"),
        details={"reason": payload.reason if payload else ""},
    )

    return {"status": "revoked", "assignment_id": str(assignment_id)}


def get_my_permissions(request: HttpRequest) -> UserPermissionsResponse:
    """Get the current user's effective permissions and roles.

    Args:
        request: HTTP request with authenticated user.

    Returns:
        Full permission and role information for the current user.
    """
    user = get_user(request)
    return UserPermissionsResponse(
        user_id=user.user_id,
        username=user.username,
        tenant_id=user.tenant_id,
        roles=user.roles,
        permissions=user.permissions,
        workspace_roles=user.workspace_roles,
        is_superadmin=user.is_superadmin(),
        is_tenant_admin=user.is_tenant_admin(),
    )


def get_my_roles(request: HttpRequest) -> UserRolesResponse:
    """Get the current user's assigned roles.

    Args:
        request: HTTP request with authenticated user.

    Returns:
        Role information for the current user.
    """
    user = get_user(request)
    return UserRolesResponse(
        user_id=user.user_id,
        username=user.username,
        tenant_id=user.tenant_id,
        roles=user.roles,
        workspace_roles=user.workspace_roles,
    )
