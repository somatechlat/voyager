"""RBAC API views for Voyager.

Creates the Ninja router and registers all endpoint functions from
submodules for roles, permissions, assignments, and workspaces.
"""

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.rbac.serializers import (
    PermissionListResponse,
    RoleAssignmentListResponse,
    RoleAssignmentSchema,
    RoleDetailResponse,
    RoleListResponse,
    RoleSchema,
    UserPermissionsResponse,
    UserRolesResponse,
    WorkspaceDetailResponse,
    WorkspaceListResponse,
    WorkspaceSchema,
)

from .assignments import (
    assign_role,
    get_my_permissions,
    get_my_roles,
    list_role_assignments,
    revoke_role_assignment,
)
from .permissions import list_permissions
from .roles import create_role, delete_role, get_role, list_roles, update_role
from .workspaces import (
    create_workspace,
    delete_workspace,
    get_workspace,
    list_workspaces,
    update_workspace,
)

router = Router(auth=VoyagerKeycloakBearer())

# Role endpoints
router.get("/roles", response=RoleListResponse)(list_roles)
router.post("/roles", response=RoleSchema)(create_role)
router.get("/roles/{role_id}", response=RoleDetailResponse)(get_role)
router.put("/roles/{role_id}", response=RoleSchema)(update_role)
router.delete("/roles/{role_id}")(delete_role)

# Permission endpoints
router.get("/permissions", response=PermissionListResponse)(list_permissions)

# Assignment endpoints
router.get("/role-assignments", response=RoleAssignmentListResponse)(list_role_assignments)
router.post("/role-assignments", response=RoleAssignmentSchema)(assign_role)
router.delete("/role-assignments/{assignment_id}")(revoke_role_assignment)

# Current user endpoints
router.get("/users/me/permissions", response=UserPermissionsResponse)(get_my_permissions)
router.get("/users/me/roles", response=UserRolesResponse)(get_my_roles)

# Workspace endpoints
router.get("/workspaces", response=WorkspaceListResponse)(list_workspaces)
router.post("/workspaces", response=WorkspaceSchema)(create_workspace)
router.get("/workspaces/{workspace_id}", response=WorkspaceDetailResponse)(get_workspace)
router.put("/workspaces/{workspace_id}", response=WorkspaceSchema)(update_workspace)
router.delete("/workspaces/{workspace_id}")(delete_workspace)
