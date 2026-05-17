"""
RBAC middleware for Voyager.

Provides Django middleware that injects authenticated user information into
each request, enforces role-based and permission-based access control, and
handles workspace-scoped authorization. Integrates with the VoyagerKeycloakAuth
system and supports both global (tenant-level) and workspace-level enforcement.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional

from django.http import HttpResponse, JsonResponse
from ninja.errors import HttpError

from apps.rbac.auth import (
    VoyagerUser,
    VoyagerKeycloakAuth,
    get_auth,
    get_optional_user,
)

logger = logging.getLogger(__name__)


class RBACMiddleware:
    """Injects authenticated user and permissions into every request.

    This middleware runs after Django's ``AuthenticationMiddleware`` and
    before any view processing. It:

    1. Extracts the Bearer token from the ``Authorization`` header.
    2. Validates the JWT using ``VoyagerKeycloakAuth.validate_token()``.
    3. Attaches the resulting ``VoyagerUser`` to ``request.user`` and
       ``request.auth``.
    4. Sets context variables for tenant and user IDs.
    5. Optionally enforces tenant header alignment.

    The middleware does **not** block requests — it only populates the user.
    Enforcement is handled by ``PermissionMiddleware`` or Ninja dependencies.

    Attributes:
        get_response: Django get_response callable.
    """

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        """Process the request through RBAC injection.

        Args:
            request: Django HTTP request object.

        Returns:
            The HTTP response from downstream handlers.
        """
        start_time = time.monotonic()

        user = self._extract_user_from_token(request)
        if user is not None:
            request.user = user
            request.auth = user
            request.voyager_user = user

            # Validate tenant alignment
            self._validate_tenant_scope(request, user)
        else:
            # Set anonymous markers
            request.user = None
            request.auth = None
            request.voyager_user = None

        elapsed_ms = (time.monotonic() - start_time) * 1000
        if elapsed_ms > 100:
            logger.warning(
                "RBACMiddleware token extraction took %.2fms (slow)", elapsed_ms
            )

        response = self.get_response(request)

        # Add security headers related to auth
        if hasattr(response, "headers"):
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("X-Frame-Options", "DENY")

        return response

    def _extract_user_from_token(self, request: Any) -> Optional[VoyagerUser]:
        """Extract and validate the JWT from the request headers.

        Args:
            request: Django HTTP request object.

        Returns:
            ``VoyagerUser`` if a valid token is present, else ``None``.
        """
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ", 1)[1].strip()
        if not token:
            return None

        try:
            auth = get_auth()
            return auth.validate_token(token)
        except HttpError:
            # Invalid/expired token — log but don't block here
            # (endpoints with auth dependencies will enforce)
            logger.debug("Token validation failed for request to %s", request.path)
            return None
        except Exception as exc:
            logger.error("Unexpected error during token extraction: %s", exc)
            return None

    def _validate_tenant_scope(self, request: Any, user: VoyagerUser) -> None:
        """Verify that the request's X-Tenant-ID matches the user's tenant.

        Super-admins can access any tenant. For other users, a mismatch
        between the header tenant and the token tenant is logged as a warning
        but not blocked (enforcement happens at the view layer).

        Args:
            request: Django HTTP request object.
            user: The authenticated Voyager user.
        """
        header_tenant = request.headers.get("X-Tenant-ID", user.tenant_id)
        if header_tenant != user.tenant_id and not user.is_superadmin():
            logger.warning(
                "Tenant scope mismatch: user %s belongs to '%s' but "
                "request targets '%s' on %s",
                user.username,
                user.tenant_id,
                header_tenant,
                request.path,
            )


class PermissionMiddleware:
    """Field-level and resource-level permission enforcement middleware.

    This middleware enforces access control based on URL path patterns and
    HTTP methods. It can be configured with route-specific permission rules
    and automatically blocks unauthorized access before the view runs.

    Configuration example (settings.py):
    ```python
    PERMISSION_MIDDLEWARE_RULES = [
        {
            "path_prefix": "/api/v1/campaigns",
            "methods": ["POST", "PUT", "DELETE"],
            "permission": "voyager:write:campaigns",
        },
        {
            "path_prefix": "/api/v1/analytics",
            "methods": ["GET"],
            "permission": "voyager:read:analytics",
        },
    ]
    ```

    Attributes:
        get_response: Django get_response callable.
    """

    # Default rules for Voyager modules — protect mutating operations
    DEFAULT_RULES: List[Dict[str, Any]] = [
        {
            "path_prefix": "/api/v1/content",
            "methods": ["POST", "PUT", "PATCH", "DELETE"],
            "permission": "voyager:write:content",
        },
        {
            "path_prefix": "/api/v1/campaigns",
            "methods": ["POST", "PUT", "PATCH", "DELETE"],
            "permission": "voyager:write:campaigns",
        },
        {
            "path_prefix": "/api/v1/strategy",
            "methods": ["POST", "PUT", "PATCH", "DELETE"],
            "permission": "voyager:write:strategy",
        },
        {
            "path_prefix": "/api/v1/analytics",
            "methods": ["POST", "PUT", "PATCH", "DELETE"],
            "permission": "voyager:execute:sql",
        },
        {
            "path_prefix": "/api/v1/clients",
            "methods": ["POST", "PUT", "PATCH", "DELETE"],
            "permission": "voyager:write:clients",
        },
        {
            "path_prefix": "/api/v1/billing",
            "methods": ["POST", "PUT", "PATCH", "DELETE"],
            "permission": "voyager:write:invoices",
        },
        {
            "path_prefix": "/api/v1/roles",
            "methods": ["POST", "PUT", "PATCH", "DELETE"],
            "permission": "voyager:manage:workspace",
        },
    ]

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response
        self._rules = self._load_rules()

    def _load_rules(self) -> List[Dict[str, Any]]:
        """Load permission rules from Django settings or use defaults.

        Returns:
            List of rule dictionaries with path_prefix, methods, permission.
        """
        try:
            from django.conf import settings as django_settings
            return getattr(
                django_settings, "PERMISSION_MIDDLEWARE_RULES", self.DEFAULT_RULES
            )
        except Exception:
            return self.DEFAULT_RULES

    def __call__(self, request: Any) -> Any:
        """Process the request through permission enforcement.

        Args:
            request: Django HTTP request object.

        Returns:
            HTTP response, either a 403 or the downstream response.
        """
        # Only apply to API routes
        if not request.path.startswith("/api/"):
            return self.get_response(request)

        # Skip health/readiness endpoints
        if request.path in ("/health", "/ready", "/healthz", "/readyz"):
            return self.get_response(request)

        # Check matching rules
        matched_rule = self._match_rule(request)
        if matched_rule is not None:
            user = getattr(request, "voyager_user", None)
            if user is None:
                return JsonResponse(
                    {"error": "Authentication required"},
                    status=401,
                )

            required_permission = matched_rule["permission"]
            if not user.has_permission(required_permission):
                logger.warning(
                    "PermissionMiddleware blocked %s %s for user %s: "
                    "requires '%s'",
                    request.method,
                    request.path,
                    user.username,
                    required_permission,
                )
                return JsonResponse(
                    {
                        "error": "Access denied",
                        "detail": f"Permission '{required_permission}' required",
                    },
                    status=403,
                )

        return self.get_response(request)

    def _match_rule(self, request: Any) -> Optional[Dict[str, Any]]:
        """Find the first rule matching the current request path and method.

        Args:
            request: Django HTTP request object.

        Returns:
            Matching rule dict or ``None``.
        """
        for rule in self._rules:
            if request.path.startswith(rule["path_prefix"]):
                if request.method in rule["methods"]:
                    return rule
        return None


class TenantIsolationMiddleware:
    """Enforce tenant isolation at the middleware layer.

    Ensures that every API request targeting a tenant-scoped endpoint includes
    a valid ``X-Tenant-ID`` header and that the user belongs to that tenant
    (or is a super-admin).

    This middleware should run **after** ``RBACMiddleware`` so that
    ``request.voyager_user`` is already populated.
    """

    # Paths that are exempt from tenant isolation
    EXEMPT_PATHS = {
        "/health",
        "/ready",
        "/healthz",
        "/readyz",
        "/api/v1/roles",  # roles can be cross-tenant
        "/api/v1/permissions",
    }

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        """Enforce tenant isolation for the request.

        Args:
            request: Django HTTP request object.

        Returns:
            HTTP response, or 403 if tenant isolation is violated.
        """
        if not request.path.startswith("/api/"):
            return self.get_response(request)

        if any(request.path.startswith(p) for p in self.EXEMPT_PATHS):
            return self.get_response(request)

        user = getattr(request, "voyager_user", None)
        if user is None:
            # Anonymous requests allowed for read-only public endpoints
            return self.get_response(request)

        header_tenant = request.headers.get("X-Tenant-ID")
        if not header_tenant:
            # Default to user's tenant
            request.headers.__dict__["X-Tenant-ID"] = user.tenant_id
            return self.get_response(request)

        if not user.is_superadmin() and header_tenant != user.tenant_id:
            logger.warning(
                "Tenant isolation violation: user %s (tenant: %s) "
                "attempted access to tenant '%s' on %s",
                user.username,
                user.tenant_id,
                header_tenant,
                request.path,
            )
            return JsonResponse(
                {
                    "error": "Tenant isolation violation",
                    "detail": f"User does not belong to tenant '{header_tenant}'",
                },
                status=403,
            )

        return self.get_response(request)


class WorkspaceScopeMiddleware:
    """Inject workspace context from headers into the request.

    Reads the ``X-Workspace-ID`` header and attaches it to the request for
    downstream workspace-scoped permission checks.
    """

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        """Attach workspace ID to request if present in headers.

        Args:
            request: Django HTTP request object.

        Returns:
            The downstream HTTP response.
        """
        workspace_id = request.headers.get("X-Workspace-ID")
        request.workspace_id = workspace_id

        # Also set on voyager_user for convenience
        user = getattr(request, "voyager_user", None)
        if user and workspace_id:
            request.voyager_workspace_id = workspace_id

        response = self.get_response(request)
        return response
