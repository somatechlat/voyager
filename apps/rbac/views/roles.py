"""Role CRUD endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from django.http import HttpRequest
from ninja import Query
from ninja.errors import HttpError

from apps.rbac.serializers import (
    RoleCreateSchema,
    RoleDetailResponse,
    RoleListResponse,
    RoleSchema,
    RoleUpdateSchema,
)

from .stores import _assignments_db, _audit_log, _roles_db, get_user


def list_roles(
    request: HttpRequest,
    search: str | None = Query(None, description="Filter by role name"),
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
    user = get_user(request)
    if not user.has_permission("voyager:read:*"):
        raise HttpError(403, "Permission denied: voyager:read:* required")

    all_roles = list(_roles_db.values())

    if search:
        search_lower = search.lower()
        all_roles = [r for r in all_roles if search_lower in r["name"].lower()]

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
    user = get_user(request)
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

    _audit_log("role.created", user, payload.name)

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
    user = get_user(request)
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
    inherited_perms: list[str] = []
    parent_id = role_data.get("parent_id")
    if parent_id:
        parent = _roles_db.get(str(parent_id))
        if parent:
            inherited_perms = list(parent["permissions"])

    total_perms = list(set(role_data["permissions"] + inherited_perms))

    # Count assignments for this role
    user_count = sum(1 for a in _assignments_db.values() if str(a.get("role_id")) == str(role_id))

    return RoleDetailResponse(
        role=role,
        inherited_permissions=inherited_perms,
        total_permissions=total_perms,
        user_count=user_count,
    )


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
    user = get_user(request)
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

    _audit_log("role.updated", user, role_data["name"])

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


def delete_role(
    request: HttpRequest,
    role_id: UUID,
) -> dict[str, str]:
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
    user = get_user(request)
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
    to_remove = [aid for aid, a in _assignments_db.items() if str(a.get("role_id")) == str(role_id)]
    for aid in to_remove:
        del _assignments_db[aid]

    _audit_log("role.deleted", user, role_name)

    return {"status": "deleted", "role_id": str(role_id)}
