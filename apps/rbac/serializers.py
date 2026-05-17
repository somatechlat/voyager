"""
Pydantic schemas (Django Ninja Serializers) for Voyager RBAC.

Defines request/response models for roles, permissions, role assignments,
and workspaces. All schemas use strict typing and validation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from ninja import Schema

# ---------------------------------------------------------------------------
# Permission schemas
# ---------------------------------------------------------------------------


class PermissionSchema(Schema):
    """Represents a single granular permission in the Voyager system.

    Attributes:
        id: Unique UUID for the permission record.
        codename: Machine-readable permission string (e.g. ``"voyager:read:analytics"``).
        name: Human-readable display name.
        module: Functional module this permission belongs to (e.g. ``"content_creation"``).
        action: Action type (e.g. ``"read"``, ``"write"``, ``"delete"``, ``"manage"``).
    """

    id: UUID
    codename: str
    name: str
    module: str
    action: str


class PermissionListResponse(Schema):
    """Paginated response for permission listing."""

    items: list[PermissionSchema]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Role schemas
# ---------------------------------------------------------------------------


class RoleSchema(Schema):
    """Represents a role definition in the Voyager RBAC system.

    Attributes:
        id: Unique UUID for the role.
        name: Role name with ``voyager-`` prefix (e.g. ``"voyager-marketing-manager"``).
        description: Human-readable description of the role's purpose.
        parent_id: Optional UUID of a parent role for hierarchical inheritance.
        permissions: List of permission codenames granted by this role.
        is_system: ``True`` for built-in roles that cannot be deleted.
        created_at: Timestamp of role creation.
        updated_at: Timestamp of last modification.
    """

    id: UUID
    name: str
    description: str
    parent_id: UUID | None = None
    permissions: list[str]
    is_system: bool
    created_at: datetime
    updated_at: datetime


class RoleListResponse(Schema):
    """Paginated response for role listing."""

    items: list[RoleSchema]
    total: int
    page: int
    page_size: int


class RoleCreateSchema(Schema):
    """Request body for creating a new role.

    Attributes:
        name: Role name. Should use ``voyager-`` prefix for consistency.
        description: Optional human-readable description.
        parent_id: Optional parent role for permission inheritance.
        permissions: List of permission codenames to assign.
    """

    name: str
    description: str = ""
    parent_id: UUID | None = None
    permissions: list[str] = []


class RoleUpdateSchema(Schema):
    """Request body for updating an existing role.

    System roles (``is_system=True``) can only have their description
    and permission list modified.
    """

    name: str | None = None
    description: str | None = None
    parent_id: UUID | None = None
    permissions: list[str] | None = None


class RoleDetailResponse(Schema):
    """Detailed role response including inherited permissions."""

    role: RoleSchema
    inherited_permissions: list[str]
    total_permissions: list[str]
    user_count: int


# ---------------------------------------------------------------------------
# Role Assignment schemas
# ---------------------------------------------------------------------------


class RoleAssignmentSchema(Schema):
    """Represents a role granted to a user within a tenant/workspace scope.

    Attributes:
        id: Unique UUID for the assignment record.
        user_id: Keycloak ``sub`` of the user receiving the role.
        role: The role being assigned.
        tenant_id: Tenant scope for the assignment.
        workspace_id: Optional workspace scope for the assignment.
        granted_by: Keycloak ``sub`` of the user who made the assignment.
        granted_at: Timestamp when the assignment was created.
        expires_at: Optional expiration timestamp for time-bound access.
    """

    id: UUID
    user_id: str
    role: RoleSchema
    tenant_id: str
    workspace_id: str | None = None
    granted_by: str
    granted_at: datetime
    expires_at: datetime | None = None


class RoleAssignmentListResponse(Schema):
    """Paginated response for role assignment listing."""

    items: list[RoleAssignmentSchema]
    total: int
    page: int
    page_size: int


class RoleAssignmentCreateSchema(Schema):
    """Request body for assigning a role to a user.

    Attributes:
        user_id: Keycloak ``sub`` of the target user.
        role_id: UUID of the role to assign.
        tenant_id: Tenant scope for the assignment.
        workspace_id: Optional workspace to scope the role to.
        expires_at: Optional expiration datetime (ISO-8601).
    """

    user_id: str
    role_id: UUID
    tenant_id: str
    workspace_id: str | None = None
    expires_at: datetime | None = None


class RoleAssignmentRevokeSchema(Schema):
    """Request body for revoking a role assignment."""

    assignment_id: UUID
    reason: str = ""


# ---------------------------------------------------------------------------
# Workspace schemas
# ---------------------------------------------------------------------------


class WorkspaceSchema(Schema):
    """Represents a workspace within a tenant for resource isolation.

    Attributes:
        id: Unique UUID for the workspace.
        name: Display name of the workspace.
        slug: URL-safe identifier.
        tenant_id: Owning tenant identifier.
        description: Optional human-readable description.
        is_active: Whether the workspace is currently enabled.
        created_at: Timestamp of creation.
        updated_at: Timestamp of last modification.
    """

    id: UUID
    name: str
    slug: str
    tenant_id: str
    description: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WorkspaceListResponse(Schema):
    """Paginated response for workspace listing."""

    items: list[WorkspaceSchema]
    total: int
    page: int
    page_size: int


class WorkspaceCreateSchema(Schema):
    """Request body for creating a new workspace.

    Attributes:
        name: Human-readable workspace name.
        slug: URL-safe unique identifier.
        tenant_id: Owning tenant identifier.
        description: Optional description.
    """

    name: str
    slug: str
    tenant_id: str
    description: str = ""


class WorkspaceUpdateSchema(Schema):
    """Request body for updating a workspace."""

    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class WorkspaceMemberSchema(Schema):
    """Represents a user's membership in a workspace."""

    user_id: str
    username: str
    email: str
    roles: list[str]
    joined_at: datetime


class WorkspaceDetailResponse(Schema):
    """Detailed workspace response with member list."""

    workspace: WorkspaceSchema
    members: list[WorkspaceMemberSchema]
    member_count: int


# ---------------------------------------------------------------------------
# User permission / role schemas
# ---------------------------------------------------------------------------


class UserPermissionsResponse(Schema):
    """Response containing the current user's effective permissions."""

    user_id: str
    username: str
    tenant_id: str
    roles: list[str]
    permissions: list[str]
    workspace_roles: dict[str, list[str]]
    is_superadmin: bool
    is_tenant_admin: bool


class UserRolesResponse(Schema):
    """Response containing the current user's assigned roles."""

    user_id: str
    username: str
    tenant_id: str
    roles: list[str]
    workspace_roles: dict[str, list[str]]


# ---------------------------------------------------------------------------
# Audit / activity schemas
# ---------------------------------------------------------------------------


class RoleActivitySchema(Schema):
    """Represents an audit event for role-related changes."""

    id: UUID
    action: str  # "role.created", "role.assigned", "role.revoked"
    actor_id: str
    target_user_id: str | None = None
    role_name: str
    tenant_id: str
    workspace_id: str | None = None
    timestamp: datetime
    details: dict[str, Any] = {}
