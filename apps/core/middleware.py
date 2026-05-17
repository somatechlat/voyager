"""
Voyager API Middleware.

Request ID, Tenant, User context, API Version, RBAC, and Audit handling.
Extends Voyant's middleware pattern with Voyager-specific middleware.
"""

from __future__ import annotations

import logging
import re
import uuid
from contextvars import ContextVar

from django.http import JsonResponse

logger = logging.getLogger(__name__)

# Context variables for request-scoped data
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="default")
api_version_var: ContextVar[str] = ContextVar("api_version", default="v1")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")
traceparent_var: ContextVar[str] = ContextVar("traceparent", default="")
authorization_var: ContextVar[str] = ContextVar("authorization", default="")

SUPPORTED_VERSIONS = ["v1"]
DEFAULT_VERSION = "v1"
CURRENT_VERSION = "v1"

VERSION_PATTERN = re.compile(r"application/vnd\.voyager\.v(\d+)\+json")


class RequestIdMiddleware:
    """Assigns or propagates a unique request ID for every incoming request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_var.set(request_id)
        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        return response


class TenantMiddleware:
    """Extracts tenant ID from request headers for multi-tenancy support."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant_id = request.headers.get("X-Tenant-ID", "default")
        tenant_id_var.set(tenant_id)
        return self.get_response(request)


class UserContextMiddleware:
    """Extracts user context from request headers for audit and RBAC."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_id_var.set(request.headers.get("X-User-ID", ""))
        traceparent_var.set(request.headers.get("traceparent", ""))
        authorization_var.set(request.headers.get("Authorization", ""))
        return self.get_response(request)


class APIVersionMiddleware:
    """Handles API version negotiation via headers and Accept header."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path in ("/health", "/healthz", "/ready", "/readyz", "/status", "/version"):
            return self.get_response(request)

        version = self._extract_version(request)
        if version and f"v{version}" not in SUPPORTED_VERSIONS:
            return JsonResponse(
                {
                    "error": "Not Acceptable",
                    "message": f"API version v{version} is not supported",
                    "supported_versions": SUPPORTED_VERSIONS,
                    "current_version": CURRENT_VERSION,
                },
                status=406,
                headers={"X-API-Version": CURRENT_VERSION},
            )

        api_version = f"v{version}" if version else DEFAULT_VERSION
        api_version_var.set(api_version)
        response = self.get_response(request)
        response["X-API-Version"] = api_version
        return response

    def _extract_version(self, request) -> str | None:
        if header_version := request.headers.get("X-API-Version"):
            return header_version.lstrip("v")

        accept = request.headers.get("Accept", "")
        match = VERSION_PATTERN.search(accept)
        if match:
            return match.group(1)
        return None


class RBACMiddleware:
    """
    RBAC enforcement middleware.

    Attaches user roles and permissions to the request object
    for downstream RBAC checks in view layers.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip RBAC for unauthenticated health endpoints
        if request.path in ("/health", "/healthz", "/ready", "/readyz", "/status", "/version"):
            return self.get_response(request)

        # Attempt to enrich request with user context from auth header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from apps.rbac.auth import get_auth

                token = auth_header.split(" ", 1)[1].strip()
                user = get_auth().validate_token(token)
                request.voyager_user = user  # type: ignore[attr-defined]
            except Exception:
                # Authentication failures are handled by the auth layer, not middleware
                pass

        return self.get_response(request)


class AuditMiddleware:
    """
    Audit logging middleware.

    Logs all mutating requests (POST, PUT, PATCH, DELETE) to the audit log.
    Non-blocking: audit failures do not affect the response.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Log mutating operations
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            try:
                self._log_request(request, response)
            except Exception as exc:
                logger.warning("Audit logging failed: %s", exc)

        return response

    def _log_request(self, request, response):
        """Write audit log entry for mutating request."""
        try:
            from apps.audit.service import log_audit_event

            user = getattr(request, "voyager_user", None)
            log_audit_event(
                tenant_id=tenant_id_var.get(),
                actor_id=getattr(user, "user_id", "anonymous") if user else "anonymous",
                actor_type="user" if user else "anonymous",
                action=f"{request.method.lower()}.{request.path.strip('/').replace('/', '.')}",
                resource_type=request.path.strip("/").split("/")[0] if request.path else "unknown",
                resource_id="",
                outcome="success" if response.status_code < 400 else "failure",
                details={
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                },
                ip_address=self._get_client_ip(request),
                user_agent=request.headers.get("User-Agent", ""),
                request_id=request_id_var.get(),
            )
        except Exception:
            # Audit logging must never break the request
            pass

    @staticmethod
    def _get_client_ip(request):
        """Extract client IP from request, handling proxies."""
        x_forwarded_for = request.headers.get("X-Forwarded-For", "")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")


# ---------------------------------------------------------------------------
# Accessor functions for context variables
# ---------------------------------------------------------------------------


def get_request_id() -> str:
    return request_id_var.get()


def get_tenant_id(request=None) -> str:
    """
    Retrieve the tenant ID for the current request context.

    If a Django request is provided, prefer the header value to avoid surprises
    when callers still pass the request object. Otherwise, fall back to the
    contextvar set by TenantMiddleware.
    """
    if request is not None:
        return request.headers.get("X-Tenant-ID", tenant_id_var.get())
    return tenant_id_var.get()


def get_api_version() -> str:
    return api_version_var.get()


def get_user_id() -> str:
    return user_id_var.get()


def get_traceparent() -> str:
    return traceparent_var.get()


def get_authorization() -> str:
    return authorization_var.get()


def get_version_info() -> dict:
    return {
        "current_version": CURRENT_VERSION,
        "supported_versions": SUPPORTED_VERSIONS,
        "default_version": DEFAULT_VERSION,
        "accept_format": "application/vnd.voyager.{version}+json",
    }
