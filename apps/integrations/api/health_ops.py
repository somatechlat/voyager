"""Health monitoring and circuit breaker endpoints."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from django.shortcuts import get_object_or_404

from apps.integrations.api import router
from apps.integrations.api.helpers import get_tenant_id, get_user_id
from apps.integrations.models import PlatformConnection, PlatformHealth
from apps.integrations.serializers import CircuitBreakerResetIn
from apps.integrations.services.gateway import (
    check_rate_limit,
    circuit_registry,
    get_circuit_breaker,
    reset_circuit_breaker,
)
from apps.integrations.services.health import (
    check_all_connections,
    get_connection_health_summary,
)


@router.get("/connections/{connection_id}/health", response={200: dict}, tags=["Integrations"])
def get_health(request: HttpRequest, connection_id: str) -> dict[str, Any]:
    """Get health summary for a connection."""
    get_object_or_404(PlatformConnection, id=connection_id, tenant_id=get_tenant_id(request))
    return get_connection_health_summary(connection_id)


@router.post("/health/check", response={200: dict}, tags=["Integrations"])
def bulk_health_check(request: HttpRequest) -> dict[str, Any]:
    """Run health checks for all connections."""
    return check_all_connections(get_tenant_id(request))


@router.get("/health/recent", response={200: list}, tags=["Integrations"])
def recent_health_checks(request: HttpRequest, limit: int = 50) -> list[PlatformHealth]:
    """Get recent health check records."""
    return list(
        PlatformHealth.objects.filter(connection__tenant_id=get_tenant_id(request)).order_by(
            "-last_check_at"
        )[:limit]
    )


@router.get("/rate-limit", response={200: dict}, tags=["Integrations"])
def rate_limit_status(request: HttpRequest) -> dict[str, Any]:
    """Check current rate-limit status for the tenant."""
    result = check_rate_limit(
        tenant_id=get_tenant_id(request),
        user_id=get_user_id(request) or "anonymous",
        endpoint=request.path,
    )
    return {
        "allowed": result.allowed,
        "remaining": result.remaining,
        "limit": result.limit,
        "retry_after": result.retry_after,
    }


@router.get("/circuit/{service_id}", response={200: dict}, tags=["Integrations"])
def get_circuit_status(request: HttpRequest, service_id: str) -> dict[str, Any]:
    """Get circuit breaker status for a service."""
    breaker = get_circuit_breaker(service_id)
    return {
        "service_id": breaker.service_id,
        "state": breaker.state.value,
        "consecutive_failures": breaker.consecutive_failures,
        "half_open_successes": breaker.half_open_successes,
        "retry_after": breaker.retry_after(),
    }


@router.post("/circuit/reset", tags=["Integrations"])
def reset_circuit(request: HttpRequest, payload: CircuitBreakerResetIn) -> dict[str, Any]:
    """Manually reset a circuit breaker to CLOSED."""
    reset_circuit_breaker(payload.service_id)
    breaker = get_circuit_breaker(payload.service_id)
    return {
        "service_id": payload.service_id,
        "state": breaker.state.value,
        "message": "Circuit breaker reset to CLOSED",
    }


@router.get("/circuit", response={200: list}, tags=["Integrations"])
def list_circuits(request: HttpRequest) -> list[dict[str, Any]]:
    """List all circuit breaker statuses."""
    return [
        {
            "service_id": cb.service_id,
            "state": cb.state.value,
            "consecutive_failures": cb.consecutive_failures,
            "half_open_successes": cb.half_open_successes,
            "retry_after": cb.retry_after(),
        }
        for cb in circuit_registry.values()
    ]
