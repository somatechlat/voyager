"""
Vault middleware for Voyager.

Provides Django middleware for HashiCorp Vault health monitoring and
connectivity verification during application startup.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from django.http import JsonResponse

from apps.vault_integration.client import vault_client

logger = logging.getLogger(__name__)


class VaultHealthMiddleware:
    """Check Vault connectivity on startup and periodically during requests.

    This lightweight middleware verifies that Vault is reachable on the
    first request and caches the result. It does **not** block requests —
    failures are logged and exposed via a response header.

    Attributes:
        get_response: Django get_response callable.
        _vault_healthy: Cached health status from last check.
        _last_check: Monotonic timestamp of last health check.
        _check_interval_seconds: Minimum seconds between health checks.
    """

    _vault_healthy: bool = True
    _last_check: float = 0.0
    _check_interval_seconds: float = 60.0

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        """Process request with optional Vault health check.

        Args:
            request: Django HTTP request object.

        Returns:
            HTTP response with ``X-Vault-Status`` header.
        """
        response = self.get_response(request)

        # Only check health periodically, not on every request
        now = time.monotonic()
        if now - self._last_check > self._check_interval_seconds:
            self._check_vault_health()
            self._last_check = now

        if hasattr(response, "headers"):
            status = "healthy" if self._vault_healthy else "unhealthy"
            response.headers["X-Vault-Status"] = status

        return response

    def _check_vault_health(self) -> None:
        """Perform a lightweight Vault connectivity check."""
        try:
            is_auth = vault_client.is_authenticated()
            self._vault_healthy = is_auth
            if not is_auth:
                logger.warning("Vault health check: authentication failed")
        except Exception as exc:
            self._vault_healthy = False
            logger.error("Vault health check failed: %s", exc)


def vault_health_view(request: Any) -> JsonResponse:
    """Django view for explicit Vault health status.

    Returns:
        JSON response with Vault connectivity status.
    """
    try:
        healthy = vault_client.is_authenticated()
        return JsonResponse(
            {
                "status": "healthy" if healthy else "unhealthy",
                "service": "vault",
            },
            status=200 if healthy else 503,
        )
    except Exception as exc:
        logger.error("Vault health view error: %s", exc)
        return JsonResponse(
            {"status": "unhealthy", "service": "vault", "error": str(exc)},
            status=503,
        )
