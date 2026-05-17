"""
Voyager Authentication extending Voyant's KeycloakAuth pattern.

This module implements JWT authentication and role-based authorization for the
Voyager marketing automation platform. It extends Voyant's ``KeycloakAuth`` and
``KeycloakBearer`` classes with Voyager-specific roles, workspace-scoped access
control, and granular marketing permissions.

Patterns inherited from Voyant:
- JWKS caching with httpx
- RS256 token validation via python-jose
- ``get_auth()`` singleton factory
- ``HttpBearer`` integration with Django Ninja
- ``require_role`` / ``require_permission`` dependency factories
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

import httpx
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from ninja.errors import HttpError
from ninja.security import HttpBearer

from apps.core.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Voyager role namespace — all marketing platform roles use this prefix.
VOYAGER_ROLE_PREFIX: str = "voyager-"

# The super-admin role grants unconditional access across all tenants and
# workspaces.
VOYAGER_SUPERADMIN: str = f"{VOYAGER_ROLE_PREFIX}superadmin"


# ---------------------------------------------------------------------------
# VoyagerUser dataclass
# ---------------------------------------------------------------------------

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
    roles: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    token: str = ""
    workspace_roles: Dict[str, List[str]] = field(default_factory=dict)

    # -- role checks ---------------------------------------------------------

    def has_role(self, role: str) -> bool:
        """Check if the user possesses *role* or is super-admin.

        Args:
            role: Role name to verify (e.g. ``"voyager-marketing-manager"``).

        Returns:
            ``True`` if the role is present or the user is super-admin.
        """
        return role in self.roles or VOYAGER_SUPERADMIN in self.roles

    def has_any_role(self, roles: List[str]) -> bool:
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

    def has_any_permission(self, permissions: List[str]) -> bool:
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
        return (
            f"{VOYAGER_ROLE_PREFIX}tenant-admin" in self.roles
            or self.is_superadmin()
        )

    def is_workspace_admin(self, workspace_id: Optional[str] = None) -> bool:
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

    def to_dict(self) -> Dict[str, Any]:
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


# ---------------------------------------------------------------------------
# VoyagerKeycloakAuth — extends Voyant's KeycloakAuth
# ---------------------------------------------------------------------------

class VoyagerKeycloakAuth:
    """JWT validator and user builder for Voyager, extending Voyant's pattern.

    Fetches and caches the Keycloak JWKS, validates RS256 token signatures,
    extracts claims, and derives Voyager-specific permissions from role
    assignments. Supports both realm roles and resource_access roles.

    Role to permission mapping covers all Voyager marketing platform roles
    from super-admin down to read-only guest access.
    """

    # -- Voyager role -> permission mapping ----------------------------------

    VOYAGER_ROLE_MAP: Dict[str, List[str]] = {
        VOYAGER_SUPERADMIN: ["*"],
        f"{VOYAGER_ROLE_PREFIX}tenant-admin": ["voyager:*"],
        f"{VOYAGER_ROLE_PREFIX}workspace-admin": [
            "voyager:read:*",
            "voyager:write:*",
            "voyager:manage:workspace",
        ],
        f"{VOYAGER_ROLE_PREFIX}creative-director": [
            "voyager:read:*",
            "voyager:write:content",
            "voyager:write:campaigns",
            "voyager:approve:content",
        ],
        f"{VOYAGER_ROLE_PREFIX}marketing-manager": [
            "voyager:read:*",
            "voyager:write:campaigns",
            "voyager:write:strategy",
            "voyager:read:analytics",
        ],
        f"{VOYAGER_ROLE_PREFIX}content-creator": [
            "voyager:read:content",
            "voyager:write:content",
            "voyager:read:assets",
        ],
        f"{VOYAGER_ROLE_PREFIX}analyst": [
            "voyager:read:analytics",
            "voyager:read:reports",
            "voyager:execute:sql",
            "voyager:export:data",
        ],
        f"{VOYAGER_ROLE_PREFIX}client-manager": [
            "voyager:read:clients",
            "voyager:write:clients",
            "voyager:read:projects",
            "voyager:write:projects",
        ],
        f"{VOYAGER_ROLE_PREFIX}billing-manager": [
            "voyager:read:billing",
            "voyager:write:invoices",
            "voyager:read:financial",
        ],
        f"{VOYAGER_ROLE_PREFIX}compliance-officer": [
            "voyager:read:*",
            "voyager:manage:compliance",
            "voyager:audit:*",
        ],
        f"{VOYAGER_ROLE_PREFIX}viewer": [
            "voyager:read:dashboards",
            "voyager:read:reports",
        ],
        f"{VOYAGER_ROLE_PREFIX}guest": [
            "voyager:read:limited",
        ],
    }

    def __init__(self) -> None:
        """Initialise the Keycloak auth client from Voyager settings."""
        settings = get_settings()
        self._server_url = settings.keycloak_url
        self._realm = settings.keycloak_realm
        self.client_id = settings.keycloak_client_id
        self.client_secret = settings.keycloak_client_secret
        self._jwks: Optional[Dict[str, Any]] = None
        self._update_urls()

    # -- properties ----------------------------------------------------------

    @property
    def server_url(self) -> str:
        return self._server_url

    @server_url.setter
    def server_url(self, value: str) -> None:
        self._server_url = value
        self._update_urls()

    @property
    def realm(self) -> str:
        return self._realm

    @realm.setter
    def realm(self, value: str) -> None:
        self._realm = value
        self._update_urls()

    def _update_urls(self) -> None:
        """Rebuild JWKS and issuer URLs after server/realm changes."""
        self._jwks_url = (
            f"{self._server_url}/realms/{self._realm}/protocol/openid-connect/certs"
        )
        self._issuer = f"{self._server_url}/realms/{self._realm}"

    # -- JWKS ----------------------------------------------------------------

    def _get_jwks(self) -> Dict[str, Any]:
        """Fetch and cache the Keycloak JWKS.

        Returns:
            The JWKS dictionary containing public signing keys.

        Raises:
            HttpError: 503 if Keycloak is unreachable.
        """
        if self._jwks is None:
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(self._jwks_url)
                    response.raise_for_status()
                    self._jwks = response.json()
            except httpx.HTTPError as exc:
                logger.error("Failed to fetch JWKS from Keycloak: %s", exc)
                raise HttpError(503, "Authentication service unavailable") from exc
        return self._jwks

    def refresh_jwks(self) -> None:
        """Force a JWKS cache refresh. Useful for key rotation events."""
        self._jwks = None
        logger.info("JWKS cache cleared, will refetch on next validation.")

    # -- token validation ----------------------------------------------------

    def validate_token(self, token: str) -> VoyagerUser:
        """Validate a JWT and return a fully populated ``VoyagerUser``.

        Verifies the RS256 signature using the matching key from JWKS, checks
        expiration, audience, and issuer, then extracts realm/resource roles
        and derives Voyager-specific permissions.

        Args:
            token: JWT string without the ``"Bearer "`` prefix.

        Returns:
            A ``VoyagerUser`` instance with roles and permissions populated.

        Raises:
            HttpError: 401 for invalid / expired tokens; 503 if Keycloak
                cannot be reached.
        """
        try:
            unverified = jwt.get_unverified_header(token)
            kid = unverified.get("kid")

            jwks = self._get_jwks()
            key: Optional[Dict[str, Any]] = None
            for jwk in jwks.get("keys", []):
                if jwk.get("kid") == kid:
                    key = jwk
                    break

            if not key:
                logger.warning("JWT validation failed: kid '%s' not found in JWKS", kid)
                raise HttpError(401, "Invalid token signing key")

            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self._issuer,
            )

            # Extract core claims
            user_id = payload.get("sub", "")
            email = payload.get("email", "")
            username = payload.get("preferred_username", email)
            tenant_id = payload.get("tenant_id", "default")

            # Extract roles from realm_access + resource_access
            roles = self._extract_roles(payload)

            # Derive Voyager permissions from roles
            permissions = self._derive_permissions(roles)

            # Extract workspace-scoped roles (custom claim)
            workspace_roles = self._extract_workspace_roles(payload)

            return VoyagerUser(
                user_id=user_id,
                email=email,
                username=username,
                tenant_id=tenant_id,
                roles=roles,
                permissions=permissions,
                token=token,
                workspace_roles=workspace_roles,
            )

        except ExpiredSignatureError as exc:
            logger.warning("JWT token is expired")
            raise HttpError(401, "Token has expired") from exc
        except JWTError as exc:
            logger.error("JWT validation error: %s", exc)
            raise HttpError(401, f"Invalid authentication token: {exc}") from exc
        except HttpError:
            raise
        except Exception as exc:
            logger.exception("Unexpected error during token validation")
            raise HttpError(500, "Internal authentication error") from exc

    def _extract_roles(self, payload: Dict[str, Any]) -> List[str]:
        """Aggregate roles from ``realm_access`` and ``resource_access``.

        Args:
            payload: Decoded JWT payload dictionary.

        Returns:
            Flat list of all role names assigned to the user.
        """
        roles: List[str] = []

        realm_access = payload.get("realm_access", {})
        roles.extend(realm_access.get("roles", []))

        resource_access = payload.get("resource_access", {})
        for client_id, client_access in resource_access.items():
            client_roles = client_access.get("roles", [])
            # Prefix client-specific roles for clarity
            for cr in client_roles:
                if cr not in roles:
                    roles.append(cr)

        return roles

    def _extract_workspace_roles(
        self, payload: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Extract workspace-scoped role assignments from custom claim.

        Keycloak can emit a ``workspace_roles`` custom claim:
        ``{"workspace-uuid": ["voyager-content-creator"], ...}``

        Args:
            payload: Decoded JWT payload dictionary.

        Returns:
            Dictionary mapping workspace IDs to lists of role names.
        """
        ws_claim = payload.get("workspace_roles", {})
        if isinstance(ws_claim, dict):
            return {str(k): list(v) for k, v in ws_claim.items() if isinstance(v, (list, tuple))}
        return {}

    def _derive_permissions(self, roles: List[str]) -> List[str]:
        """Derive granular Voyager permissions from assigned roles.

        Args:
            roles: List of role names from the JWT.

        Returns:
            Deduplicated list of permission strings.
        """
        permissions: List[str] = []
        for role in roles:
            if role in self.VOYAGER_ROLE_MAP:
                permissions.extend(self.VOYAGER_ROLE_MAP[role])
        return list(set(permissions))

    def get_role_permissions(self, role: str) -> List[str]:
        """Look up the permission set for a specific Voyager role.

        Args:
            role: Role name to look up.

        Returns:
            List of permission strings for the role, empty if unknown.
        """
        return list(self.VOYAGER_ROLE_MAP.get(role, []))

    def list_defined_roles(self) -> List[str]:
        """Return all Voyager roles defined in the role map.

        Returns:
            Sorted list of role name strings.
        """
        return sorted(self.VOYAGER_ROLE_MAP.keys())

    def list_defined_permissions(self) -> List[str]:
        """Return all unique permissions across all defined roles.

        Returns:
            Sorted deduplicated list of permission strings.
        """
        perms: set[str] = set()
        for role_perms in self.VOYAGER_ROLE_MAP.values():
            perms.update(role_perms)
        return sorted(perms)


# ---------------------------------------------------------------------------
# VoyagerKeycloakBearer — Django Ninja HttpBearer
# ---------------------------------------------------------------------------

class VoyagerKeycloakBearer(HttpBearer):
    """Django Ninja ``HttpBearer`` using Keycloak JWT validation for Voyager.

    Usage:
        ```python
        from ninja import Router
        from apps.rbac.auth import VoyagerKeycloakBearer

        router = Router(auth=VoyagerKeycloakBearer())

        @router.get("/campaigns")
        def list_campaigns(request):
            user = request.auth  # VoyagerUser instance
            ...
        ```
    """

    def authenticate(self, request, token: str) -> Optional[VoyagerUser]:
        """Authenticate an incoming request by validating the Bearer token.

        Args:
            request: Django HTTP request object.
            token: JWT token extracted from the ``Authorization`` header.

        Returns:
            A ``VoyagerUser`` if the token is valid, otherwise ``None``.

        Raises:
            HttpError: 401 if the token is invalid or expired.
        """
        return get_auth().validate_token(token)


# ---------------------------------------------------------------------------
# Singleton & helpers
# ---------------------------------------------------------------------------

_voyager_auth: Optional[VoyagerKeycloakAuth] = None


def get_auth() -> VoyagerKeycloakAuth:
    """Return the singleton ``VoyagerKeycloakAuth`` instance.

    Ensures JWKS caching and settings are loaded exactly once.

    Returns:
        The cached ``VoyagerKeycloakAuth`` instance.
    """
    global _voyager_auth
    if _voyager_auth is None:
        _voyager_auth = VoyagerKeycloakAuth()
    return _voyager_auth


def _get_bearer_token(request) -> Optional[str]:
    """Extract the Bearer token string from the request's Authorization header.

    Args:
        request: Django HTTP request object.

    Returns:
        The token string without the ``"Bearer "`` prefix, or ``None``.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None


def get_current_user(request) -> VoyagerUser:
    """Get the authenticated ``VoyagerUser`` for the current request.

    Args:
        request: Django HTTP request object.

    Returns:
        The authenticated ``VoyagerUser``.

    Raises:
        HttpError: 401 if no token is present or validation fails.
    """
    token = _get_bearer_token(request)
    if not token:
        raise HttpError(401, "Authentication required")
    return get_auth().validate_token(token)


def get_optional_user(request) -> Optional[VoyagerUser]:
    """Get the authenticated user if available, without raising on failure.

    Args:
        request: Django HTTP request object.

    Returns:
        ``VoyagerUser`` if a valid token is present, otherwise ``None``.
    """
    token = _get_bearer_token(request)
    if not token:
        return None
    try:
        return get_auth().validate_token(token)
    except HttpError:
        return None


# ---------------------------------------------------------------------------
# Ninja dependency factories
# ---------------------------------------------------------------------------

def require_role(role: str) -> Callable:
    """Create a Django Ninja dependency that enforces a required role.

    Usage:
        ```python
        @router.post("/roles", auth=require_role("voyager-tenant-admin"))
        def create_role(request, payload: RoleCreateSchema):
            ...
        ```

    Args:
        role: Role name that the authenticated user must possess.

    Returns:
        A dependency callable that returns a ``VoyagerUser`` on success.

    Raises:
        HttpError: 401 if not authenticated; 403 if role is missing.
    """

    def role_checker(request) -> VoyagerUser:
        user = get_current_user(request)
        if not user.has_role(role):
            logger.warning(
                "User %s (tenant: %s) denied access to role-protected resource "
                "requiring '%s'. User roles: %s",
                user.username,
                user.tenant_id,
                role,
                user.roles,
            )
            raise HttpError(403, f"Access denied: role '{role}' required")
        return user

    return role_checker


def require_permission(permission: str) -> Callable:
    """Create a Django Ninja dependency that enforces a required permission.

    Usage:
        ```python
        @router.get("/analytics", auth=require_permission("voyager:read:analytics"))
        def get_analytics(request):
            ...
        ```

    Args:
        permission: Permission string the user must hold.

    Returns:
        A dependency callable that returns a ``VoyagerUser`` on success.

    Raises:
        HttpError: 401 if not authenticated; 403 if permission is missing.
    """

    def permission_checker(request) -> VoyagerUser:
        user = get_current_user(request)
        if not user.has_permission(permission):
            logger.warning(
                "User %s (tenant: %s) denied access to permission-protected resource "
                "requiring '%s'. User permissions: %s",
                user.username,
                user.tenant_id,
                permission,
                user.permissions,
            )
            raise HttpError(403, f"Access denied: permission '{permission}' required")
        return user

    return permission_checker


def require_workspace_access(workspace_id_param: str = "workspace_id") -> Callable:
    """Create a Ninja dependency enforcing workspace membership.

    The workspace ID is read from either the URL path kwargs or query params.

    Args:
        workspace_id_param: Name of the parameter containing the workspace ID.

    Returns:
        Dependency callable that verifies workspace access.

    Raises:
        HttpError: 403 if the user lacks access to the workspace.
    """

    def workspace_checker(request) -> VoyagerUser:
        user = get_current_user(request)
        if user.is_superadmin() or user.is_tenant_admin():
            return user

        # Try to extract workspace_id from path or query
        ws_id = None
        if hasattr(request, "resolver_match") and request.resolver_match:
            ws_id = request.resolver_match.kwargs.get(workspace_id_param)
        if not ws_id:
            ws_id = request.GET.get(workspace_id_param)

        if ws_id and ws_id in user.workspace_roles:
            return user

        logger.warning(
            "User %s denied workspace access (workspace: %s)",
            user.username,
            ws_id,
        )
        raise HttpError(403, "Access denied: workspace membership required")

    return workspace_checker
