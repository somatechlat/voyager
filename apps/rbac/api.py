"""
RBAC API endpoints for Voyager.

Provides CRUD operations for roles, permissions, role assignments, and
workspaces. All endpoints require authentication via ``VoyagerKeycloakBearer``
and enforce appropriate permission checks.

Endpoint Summary:
- ``GET /api/v1/roles`` — List roles (paginated, filterable)
- ``POST /api/v1/roles`` — Create role (tenant-admin+)
- ``GET /api/v1/roles/{id}`` — Get role details
- ``PUT /api/v1/roles/{id}`` — Update role
- ``DELETE /api/v1/roles/{id}`` — Delete role (non-system only)
- ``GET /api/v1/permissions`` — List permissions
- ``POST /api/v1/role-assignments`` — Assign role to user
- ``DELETE /api/v1/role-assignments/{id}`` — Revoke role assignment
- ``GET /api/v1/users/me/permissions`` — Current user permissions
- ``GET /api/v1/users/me/roles`` — Current user roles
- ``GET /api/v1/workspaces`` — List workspaces
- ``POST /api/v1/workspaces`` — Create workspace
- ``GET /api/v1/workspaces/{id}`` — Get workspace details
- ``PUT /api/v1/workspaces/{id}`` — Update workspace
- ``DELETE /api/v1/workspaces/{id}`` — Delete workspace
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from django.http import HttpRequest
from ninja import Router, Query
from ninja.errors import HttpError
from ninja.pagination import paginate

from apps.rbac.auth import (
    VoyagerKeycloakBearer,
    VoyagerUser,
    get_current_user,
    require_role,
    require_permission,
)
from apps.rbac.permissions import IsTenantAdmin, IsSuperAdmin
from apps.rbac.serializers import (
    RoleSchema,
    RoleCreateSchema,
    RoleUpdateSchema,
    RoleListResponse,
    RoleDetailResponse,
    PermissionSchema,
    PermissionListResponse,
    RoleAssignmentSchema,
    RoleAssignmentCreateSchema,
    RoleAssignmentRevokeSchema,
    RoleAssignmentListResponse,
    UserPermissionsResponse,
    UserRolesResponse,
    WorkspaceSchema,
    WorkspaceCreateSchema,
    WorkspaceUpdateSchema,
    WorkspaceListResponse,
    WorkspaceDetailResponse,
    RoleActivitySchema,
)

logger = logging.getLogger(__name__)

router = Router(auth=VoyagerKeycloakBearer())

# ---------------------------------------------------------------------------
# In-memory store for demonstration (replaced by ORM models in production)
# These dictionaries simulate database tables keyed by UUID string.
# ---------------------------------------------------------------------------

_roles_db: Dict[str, Dict[str, Any]] = {}
_permissions_db: Dict[str, Dict[str, Any]] = {}
_assignments_db: Dict[str, Dict[str, Any]] = {}
_workspaces_db: Dict[str, Dict[str, Any]] = {}
_role_activity_db: List[Dict[str, Any]] = []

# Seed system roles on module load
if not _roles_db:
    from apps.rbac.auth import VoyagerKeycloakAuth

    _auth_ref = VoyagerKeycloakAuth()
    for role_name in _auth_ref.list_defined_roles():
        role_id = str(uuid4())
        perms = _auth_ref.get_role_permissions(role_name)
        _roles_db[role_id] = {
            "id": UUID(role_id),
            "name": role_name,
            "description": f"System role: {role_name}",
            "parent_id": None,
            "permissions": perms,
            "is_system": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

# Seed permissions from role map
if not _permissions_db:
    all_perms = _auth_ref.list_defined_permissions()
    for perm_codename in all_perms:
        perm_id = str(uuid4())
        parts = perm_codename.split(":")
        module = parts[1] if len(parts) > 1 else "global"
        action = parts[2] if len(parts) > 2 else "*"
        _permissions_db[perm_id] = {
            "id": UUID(perm_id),
            "codename": perm_codename,
            "name": perm_codename.replace(":", " ").title(),
            "module": module,
            "action": action,
        }


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _get_user(request: HttpRequest) -> VoyagerUser:
    """Safely extract VoyagerUser from request."""
    user = getattr(request, "auth", None)
    if user is None or not isinstance(user, VoyagerUser):
        raise HttpError(401, "Authentication required")
    return user


def _audit(
    action: str,
    actor: VoyagerUser,
    role_name: str,
    target_user_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Log a role activity event."""
    event = {
        "id": uuid4(),
        "action": action,
        "actor_id": actor.user_id,
        "target_user_id": target_user_id,
        "role_name": role_name,
        "tenant_id": actor.tenant_id,
        "workspace_id": workspace_id,
        "timestamp": datetime.utcnow(),
        "details": details or {},
    }
    _role_activity_db.append(event)
    logger.info(
        "Role activity: %s by %s (role=%s, tenant=%s)",
        action,
        actor.username,
        role_name,
        actor.tenant_id,
    )


# ---------------------------------------------------------------------------
# Role endpoints
# ---------------------------------------------------------------------------

@router.get("/roles", response=RoleListResponse)
def list_roles(
    request: HttpRequest,
    search: Optional[str] = Query(None, description="Filter by role name"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> RoleListResponse:
    """List all roles, optionally filtered by name.

    Args:
        request: HTTP request.
        search: Optional case-insensitive name filter.
        page: Page number (1-indexed).
        page_size: Items per page.

    Returns:
        Paginated role list response.
    """
    user = _get_user(request)
    if not user.has_permission("voyager:read:*"):
        raise HttpError(403, "Permission denied: voyager:read:* required")

    all_roles = list(_roles_db.values())

    if search:
        search_lower = search.lower()
        all_roles = [
            r for r in all_roles if search_lower in r["name"].lower()
        ]

    total = len(all_roles)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = all_roles[start:end]

    items = [
        RoleSchema(
            id=r["id"],
            name=r["name"],
            description=r["description"],
            parent_id=r.get("parent_id"),
            permissions=r["permissions"],
            is_system=r["is_system"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )
        for r in page_items
    ]

    return RoleListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/roles", response=RoleSchema)
def create_role(
    request: HttpRequest,
    payload: RoleCreateSchema,
) -> RoleSchema:
    """Create a new custom role.

    Args:
        request: HTTP request.
        payload: Role creation data.

    Returns:
        The newly created role.

    Raises:
        HttpError: 403 if user lacks tenant-admin role.
        HttpError: 400 if role name already exists.
    """
    user = _get_user(request)
    if not user.is_tenant_admin():
        raise HttpError(403, "Access denied: tenant admin required")

    # Check for duplicate
    for existing in _roles_db.values():
        if existing["name"].lower() == payload.name.lower():
            raise HttpError(400, f"Role '{payload.name}' already exists")

    role_id = uuid4()
    now = datetime.utcnow()
    role_data = {
        "id": role_id,
        "name": payload.name,
        "description": payload.description,
        "parent_id": payload.parent_id,
        "permissions": payload.permissions,
        "is_system": False,
        "created_at": now,
        "updated_at": now,
    }
    _roles_db[str(role_id)] = role_data

    _audit("role.created", user, payload.name)

    return RoleSchema(
        id=role_id,
        name=payload.name,
        description=payload.description,
        parent_id=payload.parent_id,
        permissions=payload.permissions,
        is_system=False,
        created_at=now,
        updated_at=now,
    )


@router.get("/roles/{role_id}", response=RoleDetailResponse)
def get_role(
    request: HttpRequest,
    role_id: UUID,
) -> RoleDetailResponse:
    """Get detailed information about a single role.

    Args:
        request: HTTP request.
        role_id: UUID of the role.

    Returns:
        Role details with inherited permissions.

    Raises:
        HttpError: 404 if role not found.
    """
    user = _get_user(request)
    if not user.has_permission("voyager:read:*"):
        raise HttpError(403, "Permission denied")

    role_data = _roles_db.get(str(role_id))
    if not role_data:
        raise HttpError(404, f"Role {role_id} not found")

    role = RoleSchema(
        id=role_data["id"],
        name=role_data["name"],
        description=role_data["description"],
        parent_id=role_data.get("parent_id"),
        permissions=role_data["permissions"],
        is_system=role_data["is_system"],
        created_at=role_data["created_at"],
        updated_at=role_data["updated_at"],
    )

    # Compute inherited permissions from parent
    inherited_perms: List[str] = []
    parent_id = role_data.get("parent_id")
    if parent_id:
        parent = _roles_db.get(str(parent_id))
        if parent:
            inherited_perms = list(parent["permissions"])

    total_perms = list(set(role_data["permissions"] + inherited_perms))

    # Count assignments for this role
    user_count = sum(
        1
        for a in _assignments_db.values()
        if str(a.get("role_id")) == str(role_id)
    )

    return RoleDetailResponse(
        role=role,
        inherited_permissions=inherited_perms,
        total_permissions=total_perms,
        user_count=user_count,
    )


@router.put("/roles/{role_id}", response=RoleSchema)
def update_role(
    request: HttpRequest,
    role_id: UUID,
    payload: RoleUpdateSchema,
) -> RoleSchema:
    """Update an existing role.

    System roles can only have description and permissions modified.

    Args:
        request: HTTP request.
        role_id: UUID of the role to update.
        payload: Update data.

    Returns:
        Updated role.

    Raises:
        HttpError: 404 if role not found.
        HttpError: 403 if modifying a system role's name.
    """
    user = _get_user(request)
    if not user.is_tenant_admin():
        raise HttpError(403, "Access denied: tenant admin required")

    role_data = _roles_db.get(str(role_id))
    if not role_data:
        raise HttpError(404, f"Role {role_id} not found")

    if role_data["is_system"]:
        if payload.name is not None and payload.name != role_data["name"]:
            raise HttpError(403, "Cannot rename system roles")
        if payload.parent_id is not None:
            raise HttpError(403, "Cannot change parent of system roles")

    if payload.name is not None:
        role_data["name"] = payload.name
    if payload.description is not None:
        role_data["description"] = payload.description
    if payload.parent_id is not None:
        role_data["parent_id"] = payload.parent_id
    if payload.permissions is not None:
        role_data["permissions"] = payload.permissions

    role_data["updated_at"] = datetime.utcnow()

    _audit("role.updated", user, role_data["name"])

    return RoleSchema(
        id=role_data["id"],
        name=role_data["name"],
        description=role_data["description"],
        parent_id=role_data.get("parent_id"),
        permissions=role_data["permissions"],
        is_system=role_data["is_system"],
        created_at=role_data["created_at"],
        updated_at=role_data["updated_at"],
    )


@router.delete("/roles/{role_id}")
def delete_role(
    request: HttpRequest,
    role_id: UUID,
) -> Dict[str, str]:
    """Delete a non-system role.

    Args:
        request: HTTP request.
        role_id: UUID of the role to delete.

    Returns:
        Success confirmation.

    Raises:
        HttpError: 404 if role not found.
        HttpError: 403 if attempting to delete a system role.
    """
    user = _get_user(request)
    if not user.is_tenant_admin():
        raise HttpError(403, "Access denied: tenant admin required")

    role_data = _roles_db.get(str(role_id))
    if not role_data:
        raise HttpError(404, f"Role {role_id} not found")

    if role_data["is_system"]:
        raise HttpError(403, "System roles cannot be deleted")

    role_name = role_data["name"]
    del _roles_db[str(role_id)]

    # Remove any assignments for this role
    to_remove = [
        aid
        for aid, a in _assignments_db.items()
        if str(a.get("role_id")) == str(role_id)
    ]
    for aid in to_remove:
        del _assignments_db[aid]

    _audit("role.deleted", user, role_name)

    return {"status": "deleted", "role_id": str(role_id)}


# ---------------------------------------------------------------------------
# Permission endpoints
# ---------------------------------------------------------------------------

@router.get("/permissions", response=PermissionListResponse)
def list_permissions(
    request: HttpRequest,
    module: Optional[str] = Query(None, description="Filter by module name"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PermissionListResponse:
    """List all permissions, optionally filtered by module or action.

    Args:
        request: HTTP request.
        module: Optional module filter (e.g. ``"content_creation"``).
        action: Optional action filter (e.g. ``"read"``).
        page: Page number.
        page_size: Items per page.

    Returns:
        Paginated permission list.
    """
    user = _get_user(request)
    if not user.has_permission("voyager:read:*"):
        raise HttpError(403, "Permission denied")

    all_perms = list(_permissions_db.values())

    if module:
        all_perms = [p for p in all_perms if p["module"] == module]
    if action:
        all_perms = [p for p in all_perms if p["action"] == action]

    total = len(all_perms)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = all_perms[start:end]

    items = [
        PermissionSchema(
            id=p["id"],
            codename=p["codename"],
            name=p["name"],
            module=p["module"],
            action=p["action"],
        )
        for p in page_items
    ]

    return PermissionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# Role Assignment endpoints
# ---------------------------------------------------------------------------

@router.get("/role-assignments", response=RoleAssignmentListResponse)
def list_role_assignments(
    request: HttpRequest,
    user_id: Optional[str] = Query(None, description="Filter by user"),
    role_id: Optional[UUID] = Query(None, description="Filter by role"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    workspace_id: Optional[str] = Query(None, description="Filter by workspace"),
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
    user = _get_user(request)
    if not user.has_permission("voyager:read:*"):
        raise HttpError(403, "Permission denied")

    all_assignments = list(_assignments_db.values())

    if user_id:
        all_assignments = [a for a in all_assignments if a["user_id"] == user_id]
    if role_id:
        all_assignments = [
            a for a in all_assignments if str(a.get("role_id")) == str(role_id)
        ]
    if tenant_id:
        all_assignments = [a for a in all_assignments if a["tenant_id"] == tenant_id]
    if workspace_id:
        all_assignments = [
            a for a in all_assignments if a.get("workspace_id") == workspace_id
        ]

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


@router.post("/role-assignments", response=RoleAssignmentSchema)
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
    user = _get_user(request)
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

    _audit(
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


@router.delete("/role-assignments/{assignment_id}")
def revoke_role_assignment(
    request: HttpRequest,
    assignment_id: UUID,
    payload: Optional[RoleAssignmentRevokeSchema] = None,
) -> Dict[str, str]:
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
    user = _get_user(request)
    if not user.is_tenant_admin():
        raise HttpError(403, "Access denied: tenant admin required")

    assignment_data = _assignments_db.get(str(assignment_id))
    if not assignment_data:
        raise HttpError(404, f"Assignment {assignment_id} not found")

    role_data = _roles_db.get(str(assignment_data.get("role_id", "")), {})
    role_name = role_data.get("name", "unknown")

    del _assignments_db[str(assignment_id)]

    _audit(
        "role.revoked",
        user,
        role_name,
        target_user_id=assignment_data["user_id"],
        workspace_id=assignment_data.get("workspace_id"),
        details={"reason": payload.reason if payload else ""},
    )

    return {"status": "revoked", "assignment_id": str(assignment_id)}


# ---------------------------------------------------------------------------
# Current user endpoints
# ---------------------------------------------------------------------------

@router.get("/users/me/permissions", response=UserPermissionsResponse)
def get_my_permissions(request: HttpRequest) -> UserPermissionsResponse:
    """Get the current user's effective permissions and roles.

    Args:
        request: HTTP request with authenticated user.

    Returns:
        Full permission and role information for the current user.
    """
    user = _get_user(request)
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


@router.get("/users/me/roles", response=UserRolesResponse)
def get_my_roles(request: HttpRequest) -> UserRolesResponse:
    """Get the current user's assigned roles.

    Args:
        request: HTTP request with authenticated user.

    Returns:
        Role information for the current user.
    """
    user = _get_user(request)
    return UserRolesResponse(
        user_id=user.user_id,
        username=user.username,
        tenant_id=user.tenant_id,
        roles=user.roles,
        workspace_roles=user.workspace_roles,
    )


# ---------------------------------------------------------------------------
# Workspace endpoints
# ---------------------------------------------------------------------------

@router.get("/workspaces", response=WorkspaceListResponse)
def list_workspaces(
    request: HttpRequest,
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
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
    user = _get_user(request)
    if not user.has_permission("voyager:read:*"):
        raise HttpError(403, "Permission denied")

    all_workspaces = list(_workspaces_db.values())

    # Non-superadmins only see their tenant's workspaces
    if not user.is_superadmin():
        all_workspaces = [
            w for w in all_workspaces if w["tenant_id"] == user.tenant_id
        ]

    if tenant_id:
        all_workspaces = [
            w for w in all_workspaces if w["tenant_id"] == tenant_id
        ]
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


@router.post("/workspaces", response=WorkspaceSchema)
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
    user = _get_user(request)
    if not (
        user.is_tenant_admin()
        or user.has_permission("voyager:manage:workspace")
    ):
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

    _audit(
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


@router.get("/workspaces/{workspace_id}", response=WorkspaceDetailResponse)
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
    user = _get_user(request)
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

    member_schemas = [
        {
            "user_id": m["user_id"],
            "username": m["username"],
            "email": m["email"],
            "roles": m["roles"],
            "joined_at": m["joined_at"],
        }
        for m in members
    ]

    # Build response dict manually since WorkspaceDetailResponse expects it
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


@router.put("/workspaces/{workspace_id}", response=WorkspaceSchema)
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
    user = _get_user(request)
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


@router.delete("/workspaces/{workspace_id}")
def delete_workspace(
    request: HttpRequest,
    workspace_id: UUID,
) -> Dict[str, str]:
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
    user = _get_user(request)
    if not user.is_tenant_admin():
        raise HttpError(403, "Access denied: tenant admin required")

    ws_data = _workspaces_db.get(str(workspace_id))
    if not ws_data:
        raise HttpError(404, f"Workspace {workspace_id} not found")

    ws_data["is_active"] = False
    ws_data["updated_at"] = datetime.utcnow()

    _audit(
        "workspace.deactivated",
        user,
        ws_data["name"],
        workspace_id=str(workspace_id),
    )

    return {"status": "deactivated", "workspace_id": str(workspace_id)}
