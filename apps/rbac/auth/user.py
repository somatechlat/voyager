"""VoyagerUser dataclass for authenticated users."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Voyager role namespace — all marketing platform roles use this prefix.
VOYAGER_ROLE_PREFIX: str = "voyager-"

# The super-admin role grants unconditional access across all tenants and
# workspaces.
VOYAGER_SUPERADMIN: str = f"{VOYAGER_ROLE_PREFIX}superadmin"


@dataclass
class VoyagerUser:
    """Represents an authenticated Voyager user extracted from a Keycloak JWT.

    Attributes:
        user_id: Keycloak ``sub`` claim — the unique user identifier.
        email: User's email address.
        username: User's preferred username.
        tenant_id: Tenant the user belongs to (custom claim or ``default``).
        roles: All realm + resource roles assigned to the user.
        permissions: Derived granular permission strings from role mapping.
        token: The raw JWT bearer token.
        workspace_roles: Mapping of ``workspace_id -> [role_names]`` for
            workspace-scoped access control.
    """

    user_id: str
    email: str
    username: str
    tenant_id: str
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    token: str = ""
    workspace_roles: dict[str, list[str]] = field(default_factory=dict)

    # -- role checks ---------------------------------------------------------

    def has_role(self, role: str) -> bool:
        """Check if the user possesses *role* or is super-admin.

        Args:
            role: Role name to verify (e.g. ``"voyager-marketing-manager"``).

        Returns:
            ``True`` if the role is present or the user is super-admin.
        """
        return role in self.roles or VOYAGER_SUPERADMIN in self.roles

    def has_any_role(self, roles: list[str]) -> bool:
        """Check if the user has at least one role from the list.

        Args:
            roles: List of role names to check.

        Returns:
            ``True`` if any role matches or user is super-admin.
        """
        if VOYAGER_SUPERADMIN in self.roles:
            return True
        return any(r in self.roles for r in roles)

    def has_workspace_role(self, workspace_id: str, role: str) -> bool:
        """Check workspace-scoped role membership.

        Args:
            workspace_id: The workspace identifier.
            role: Role name to verify within that workspace.

        Returns:
            ``True`` if the user has the role in the workspace or is
            super-admin / tenant-admin.
        """
        if VOYAGER_SUPERADMIN in self.roles:
            return True
        if f"{VOYAGER_ROLE_PREFIX}tenant-admin" in self.roles:
            return True
        ws_roles = self.workspace_roles.get(workspace_id, [])
        return role in ws_roles

    # -- permission checks ---------------------------------------------------

    def has_permission(self, permission: str) -> bool:
        """Check if the user holds *permission* via role derivation.

        Supports wildcard matching:
        - ``*`` in permissions grants everything.
        - ``voyager:*`` grants all voyager-scoped permissions.
        - ``voyager:<module>:*`` grants all actions within a module.

        Args:
            permission: Permission string (e.g. ``"voyager:write:campaigns"``).

        Returns:
            ``True`` if the permission is granted.
        """
        if "*" in self.permissions or "voyager:*" in self.permissions:
            return True

        if permission in self.permissions:
            return True

        if ":" in permission:
            module, action = permission.split(":", 1)
            if f"{module}:*" in self.permissions:
                return True
            # Also check module-level wildcard: voyager:write:*
            if ":" in action:
                submodule, _ = action.split(":", 1)
                if f"{module}:{submodule}:*" in self.permissions:
                    return True

        return False

    def has_any_permission(self, permissions: list[str]) -> bool:
        """Check if the user has at least one of the listed permissions.

        Args:
            permissions: List of permission strings.

        Returns:
            ``True`` if any permission is granted.
        """
        return any(self.has_permission(p) for p in permissions)

    def is_authenticated(self) -> bool:
        """Return ``True`` if the user has a valid user_id (i.e. is authenticated)."""
        return bool(self.user_id)

    def is_superadmin(self) -> bool:
        """Return ``True`` if the user is a Voyager super-admin."""
        return VOYAGER_SUPERADMIN in self.roles

    def is_tenant_admin(self) -> bool:
        """Return ``True`` if the user is a tenant-level administrator."""
        return f"{VOYAGER_ROLE_PREFIX}tenant-admin" in self.roles or self.is_superadmin()

    def is_workspace_admin(self, workspace_id: str | None = None) -> bool:
        """Return ``True`` if the user is a workspace administrator.

        Args:
            workspace_id: Optional workspace to scope the check to.
        """
        if self.is_superadmin() or self.is_tenant_admin():
            return True
        if f"{VOYAGER_ROLE_PREFIX}workspace-admin" in self.roles:
            return True
        if workspace_id:
            ws_roles = self.workspace_roles.get(workspace_id, [])
            return f"{VOYAGER_ROLE_PREFIX}workspace-admin" in ws_roles
        return False

    def to_dict(self) -> dict[str, Any]:
        """Serialize user to a dictionary for logging or caching.

        Returns:
            Dictionary representation of the user (token excluded for safety).
        """
        return {
            "user_id": self.user_id,
            "email": self.email,
            "username": self.username,
            "tenant_id": self.tenant_id,
            "roles": self.roles,
            "permissions": self.permissions,
            "workspace_roles": self.workspace_roles,
            "is_superadmin": self.is_superadmin(),
        }
