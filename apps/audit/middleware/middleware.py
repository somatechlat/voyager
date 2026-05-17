"""AuditMiddleware — Django middleware for automatic audit logging."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from ninja.errors import HttpError

from apps.rbac.auth import get_optional_user

from .logging import _extract_action, _extract_resource, _log_entry
from .redaction import SKIP_PATHS

logger = logging.getLogger(__name__)


class AuditMiddleware:
    """Automatically log all mutating HTTP requests with hash-chain integrity.

    This middleware intercepts POST, PUT, PATCH, and DELETE requests and
    creates an immutable audit log entry with:
    - Actor identification (from JWT)
    - Action classification
    - Resource identification
    - Outcome (success/failure/denied)
    - Hash chain linking to previous entries

    Attributes:
        get_response: Django get_response callable.
    """

    # HTTP methods that trigger audit logging
    MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        """Process the request through audit logging.

        Args:
            request: Django HTTP request object.

        Returns:
            HTTP response from downstream handlers.
        """
        # Only audit mutating methods
        if request.method not in self.MUTATING_METHODS:
            return self.get_response(request)

        # Skip health/readiness and audit endpoints
        if any(request.path.startswith(p) for p in SKIP_PATHS):
            return self.get_response(request)

        # Only audit API routes
        if not request.path.startswith("/api/"):
            return self.get_response(request)

        start_time = time.monotonic()

        # Capture pre-request state
        user = get_optional_user(request)
        action = _extract_action(request)
        resource_type, resource_id = _extract_resource(request)
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        request_id = request.headers.get("X-Request-ID", "")
        tenant_id = request.headers.get("X-Tenant-ID", user.tenant_id if user else "default")

        try:
            response = self.get_response(request)
            duration_ms = (time.monotonic() - start_time) * 1000

            if self._should_log(request, response):
                outcome = "success" if response.status_code < 400 else "failure"
                _log_entry(
                    tenant_id=tenant_id,
                    user=user,
                    actor_type="user" if user else "service",
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    outcome=outcome,
                    request=request,
                    response=response,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    request_id=request_id,
                    duration_ms=duration_ms,
                )

            return response

        except HttpError as exc:
            duration_ms = (time.monotonic() - start_time) * 1000
            _log_entry(
                tenant_id=tenant_id,
                user=user,
                actor_type="user" if user else "service",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                outcome="denied" if exc.status_code == 403 else "failure",
                request=request,
                response=None,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                duration_ms=duration_ms,
                error=str(exc),
            )
            raise

        except Exception as exc:
            duration_ms = (time.monotonic() - start_time) * 1000
            _log_entry(
                tenant_id=tenant_id,
                user=user,
                actor_type="user" if user else "service",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                outcome="failure",
                request=request,
                response=None,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                duration_ms=duration_ms,
                error=str(exc),
            )
            raise

    def _should_log(self, request: Any, response: Any) -> bool:
        """Determine if the request/response pair should be logged.

        Args:
            request: Django HTTP request object.
            response: Django HTTP response object.

        Returns:
            ``True`` if the interaction should be audited.
        """
        # Always log mutating operations on API endpoints
        return True

    def _get_client_ip(self, request: Any) -> str | None:
        """Extract the client's real IP address, respecting proxies.

        Checks ``X-Forwarded-For`` and ``X-Real-IP`` headers before falling
        back to ``REMOTE_ADDR``.

        Args:
            request: Django HTTP request object.

        Returns:
            IP address string, or ``None`` if unavailable.
        """
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            # Take the first IP in the chain (closest to the client)
            return x_forwarded_for.split(",")[0].strip()

        x_real_ip = request.headers.get("X-Real-IP")
        if x_real_ip:
            return x_real_ip.strip()

        return request.META.get("REMOTE_ADDR")
