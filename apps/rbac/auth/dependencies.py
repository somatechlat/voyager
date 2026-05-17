"""Authentication dependency factories and helper functions."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from ninja.errors import HttpError

from .user import VoyagerUser

logger = logging.getLogger(__name__)

_voyager_auth: Any | None = None


def get_auth() -> Any:
    """Return the singleton ``VoyagerKeycloakAuth`` instance.

    Ensures JWKS caching and settings are loaded exactly once.

    Returns:
        The cached ``VoyagerKeycloakAuth`` instance.
    """
    global _voyager_auth
    if _voyager_auth is None:
        from .keycloak import VoyagerKeycloakAuth

        _voyager_auth = VoyagerKeycloakAuth()
    return _voyager_auth


def _get_bearer_token(request) -> str | None:
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


def get_optional_user(request) -> VoyagerUser | None:
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
