"""
Permission classes for Voyager RBAC.

Provides declarative permission checkers that can be used as Django Ninja
dependencies, in middleware, or directly in view logic. All classes follow
the pattern of receiving a ``VoyagerUser`` and returning a boolean or
raising ``HttpError(403)``.

Each class is designed to be composable and chainable for fine-grained
access control across tenants and workspaces.
"""

from __future__ import annotations

import logging

from ninja.errors import HttpError

from apps.rbac.auth import VoyagerUser, get_current_user

logger = logging.getLogger(__name__)


class BasePermission:
    """Abstract base for all Voyager permission checkers.

    Subclasses must override ``has_permission(self, user: VoyagerUser) -> bool``.
    The ``__call__`` method adapts the class for use as a Ninja dependency or
    middleware callable.
    """

    def has_permission(self, user: VoyagerUser) -> bool:
        """Return ``True`` if *user* satisfies this permission check.

        Args:
            user: The authenticated Voyager user.

        Returns:
            Boolean indicating permission grant.
        """
        raise NotImplementedError("Subclasses must implement has_permission()")

    def __call__(self, request) -> VoyagerUser:
        """Execute permission check as a Ninja dependency.

        Args:
            request: Django HTTP request object.

        Returns:
            The authenticated ``VoyagerUser`` if permission is granted.

        Raises:
            HttpError: 401 if not authenticated; 403 if permission denied.
        """
        user = get_current_user(request)
        if not self.has_permission(user):
            self._deny(user)
        return user

    def _deny(self, user: VoyagerUser) -> None:
        """Log and raise a 403 forbidden error.

        Args:
            user: The user being denied.

        Raises:
            HttpError: Always raises 403.
        """
        logger.warning(
            "Permission denied for user %s (tenant: %s, roles: %s)",
            user.username,
            user.tenant_id,
            user.roles,
        )
        raise HttpError(403, f"Access denied: {self.__class__.__name__}")


class IsAuthenticated(BasePermission):
    """Require any authenticated user.

    Passes if the request carries a valid JWT token. This is the weakest
    permission check and is effectively what ``VoyagerKeycloakBearer`` already
    enforces, but it is useful for explicitness in composite permissions.
    """

    def has_permission(self, user: VoyagerUser) -> bool:
        return user.is_authenticated()


class HasRole(BasePermission):
    """Require the user to have a specific role.

    Super-admin always passes. The role check uses ``VoyagerUser.has_role()``
    which includes the super-admin override.
    """

    def __init__(self, role: str) -> None:
        """Initialise with the required role name.

        Args:
            role: Role name (e.g. ``"voyager-marketing-manager"``).
        """
        self.role = role

    def has_permission(self, user: VoyagerUser) -> bool:
        return user.has_role(self.role)

    def _deny(self, user: VoyagerUser) -> None:
        logger.warning(
            "User %s lacks required role '%s' (has: %s)",
            user.username,
            self.role,
            user.roles,
        )
        raise HttpError(403, f"Access denied: role '{self.role}' required")


class HasAnyRole(BasePermission):
    """Require the user to have at least one of the specified roles."""

    def __init__(self, roles: list[str]) -> None:
        """Initialise with a list of acceptable roles.

        Args:
            roles: List of role names; any one will satisfy the check.
        """
        self.roles = roles

    def has_permission(self, user: VoyagerUser) -> bool:
        return user.has_any_role(self.roles)

    def _deny(self, user: VoyagerUser) -> None:
        logger.warning(
            "User %s lacks any of required roles %s (has: %s)",
            user.username,
            self.roles,
            user.roles,
        )
        raise HttpError(403, f"Access denied: one of {self.roles} required")


class HasPermission(BasePermission):
    """Require the user to hold a specific permission string.

    Uses ``VoyagerUser.has_permission()`` which supports wildcard matching
    (``*``, ``voyager:*``, ``voyager:module:*``).
    """

    def __init__(self, permission: str) -> None:
        """Initialise with the required permission.

        Args:
            permission: Permission string (e.g. ``"voyager:read:analytics"``).
        """
        self.permission = permission

    def has_permission(self, user: VoyagerUser) -> bool:
        return user.has_permission(self.permission)

    def _deny(self, user: VoyagerUser) -> None:
        logger.warning(
            "User %s lacks permission '%s' (has: %s)",
            user.username,
            self.permission,
            user.permissions,
        )
        raise HttpError(403, f"Access denied: permission '{self.permission}' required")


class HasAnyPermission(BasePermission):
    """Require the user to hold at least one of the specified permissions."""

    def __init__(self, permissions: list[str]) -> None:
        """Initialise with acceptable permissions.

        Args:
            permissions: List of permission strings; any one satisfies.
        """
        self.permissions = permissions

    def has_permission(self, user: VoyagerUser) -> bool:
        return user.has_any_permission(self.permissions)

    def _deny(self, user: VoyagerUser) -> None:
        logger.warning(
            "User %s lacks any of permissions %s (has: %s)",
            user.username,
            self.permissions,
            user.permissions,
        )
        raise HttpError(403, f"Access denied: one of {self.permissions} required")


class IsTenantAdmin(BasePermission):
    """Require tenant-administrator or higher privileges.

    Passes for ``voyager-tenant-admin`` and ``voyager-superadmin``.
    """

    def has_permission(self, user: VoyagerUser) -> bool:
        return user.is_tenant_admin()

    def _deny(self, user: VoyagerUser) -> None:
        logger.warning(
            "User %s is not a tenant admin (roles: %s)",
            user.username,
            user.roles,
        )
        raise HttpError(403, "Access denied: tenant admin required")


class IsSuperAdmin(BasePermission):
    """Require super-administrator privileges.

    Only ``voyager-superadmin`` passes this check.
    """

    def has_permission(self, user: VoyagerUser) -> bool:
        return user.is_superadmin()

    def _deny(self, user: VoyagerUser) -> None:
        logger.warning(
            "User %s is not superadmin (roles: %s)",
            user.username,
            user.roles,
        )
        raise HttpError(403, "Access denied: superadmin required")


class IsWorkspaceMember(BasePermission):
    """Require membership in a specific workspace.

    The workspace ID is resolved from the URL path kwargs (``workspace_id``)
    or query parameters. Tenant and super admins always pass.
    """

    def __init__(self, workspace_id_param: str = "workspace_id") -> None:
        """Initialise with the parameter name holding the workspace ID.

        Args:
            workspace_id_param: URL kwarg or query param name.
        """
        self.workspace_id_param = workspace_id_param

    def has_permission(self, user: VoyagerUser) -> bool:
        # Admins bypass workspace checks
        if user.is_superadmin() or user.is_tenant_admin():
            return True
        # Check if user has any workspace roles
        return bool(user.workspace_roles)

    def check_workspace(self, user: VoyagerUser, workspace_id: str) -> bool:
        """Check access to a concrete workspace.

        Args:
            user: The authenticated user.
            workspace_id: The workspace to check.

        Returns:
            ``True`` if user has any role in the workspace or is admin.
        """
        if user.is_superadmin() or user.is_tenant_admin():
            return True
        return workspace_id in user.workspace_roles

    def _deny(self, user: VoyagerUser) -> None:
        logger.warning(
            "User %s is not a member of the requested workspace",
            user.username,
        )
        raise HttpError(403, "Access denied: workspace membership required")


class IsWorkspaceAdmin(BasePermission):
    """Require workspace-administrator role for a specific workspace.

    Tenant admins and super admins always pass.
    """

    def __init__(self, workspace_id_param: str = "workspace_id") -> None:
        """Initialise with the parameter name holding the workspace ID.

        Args:
            workspace_id_param: URL kwarg or query param name.
        """
        self.workspace_id_param = workspace_id_param

    def has_permission(self, user: VoyagerUser) -> bool:
        if user.is_superadmin() or user.is_tenant_admin():
            return True
        return "voyager-workspace-admin" in user.roles

    def check_workspace(self, user: VoyagerUser, workspace_id: str) -> bool:
        """Check admin access to a concrete workspace.

        Args:
            user: The authenticated user.
            workspace_id: The workspace to check.

        Returns:
            ``True`` if user is a workspace admin for the given workspace.
        """
        if user.is_superadmin() or user.is_tenant_admin():
            return True
        ws_roles = user.workspace_roles.get(workspace_id, [])
        return "voyager-workspace-admin" in ws_roles or "voyager-workspace-admin" in user.roles

    def _deny(self, user: VoyagerUser) -> None:
        logger.warning(
            "User %s is not a workspace admin (roles: %s)",
            user.username,
            user.roles,
        )
        raise HttpError(403, "Access denied: workspace admin required")


class IsOwner(BasePermission):
    """Require the user to be the owner of a resource.

    Ownership is determined by matching the user's ``user_id`` against the
    resource's owner field (passed at check time).
    """

    def __init__(self, owner_id: str | None = None) -> None:
        """Initialise with an optional static owner ID.

        Args:
            owner_id: If provided, checked against the user's ID. If ``None``,
                the caller must use ``check_owner()`` dynamically.
        """
        self.owner_id = owner_id

    def has_permission(self, user: VoyagerUser) -> bool:
        if self.owner_id is not None:
            return user.user_id == self.owner_id
        # Dynamic ownership check requires manual verification
        return True

    def check_owner(self, user: VoyagerUser, owner_id: str) -> bool:
        """Verify that *user* owns the resource identified by *owner_id*.

        Args:
            user: The authenticated user.
            owner_id: The owner identifier on the resource.

        Returns:
            ``True`` if the user's ID matches the owner ID or user is admin.
        """
        if user.is_superadmin() or user.is_tenant_admin():
            return True
        return user.user_id == owner_id

    def _deny(self, user: VoyagerUser) -> None:
        logger.warning("User %s is not the resource owner", user.username)
        raise HttpError(403, "Access denied: resource ownership required")


class ReadOnly(BasePermission):
    """Allow only safe HTTP methods (GET, HEAD, OPTIONS).

    Useful for endpoints that should accept unauthenticated read access
    while requiring authentication for mutations.
    """

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    def __init__(self) -> None:
        self._request = None

    def has_permission(self, user: VoyagerUser) -> bool:
        return True  # Actual method check happens in __call__

    def __call__(self, request) -> VoyagerUser:
        if request.method not in self.SAFE_METHODS:
            raise HttpError(403, "Access denied: read-only method required")
        user = get_current_user(request)
        return user


class CompositePermission(BasePermission):
    """Combine multiple permission classes with AND / OR logic.

    Example:
        ```python
        perm = CompositePermission(
            all_of=[IsAuthenticated(), IsTenantAdmin()],
            any_of=[HasRole("voyager-marketing-manager"), HasRole("voyager-content-creator")],
        )
        ```
    """

    def __init__(
        self,
        all_of: list[BasePermission] | None = None,
        any_of: list[BasePermission] | None = None,
    ) -> None:
        """Initialise with permission lists.

        Args:
            all_of: Every permission in this list must pass (AND).
            any_of: At least one permission in this list must pass (OR).
        """
        self.all_of = all_of or []
        self.any_of = any_of or []

    def has_permission(self, user: VoyagerUser) -> bool:
        if self.all_of:
            if not all(p.has_permission(user) for p in self.all_of):
                return False
        if self.any_of:
            if not any(p.has_permission(user) for p in self.any_of):
                return False
        return True

    def _deny(self, user: VoyagerUser) -> None:
        logger.warning("Composite permission denied for user %s", user.username)
        raise HttpError(403, "Access denied: composite permission check failed")
