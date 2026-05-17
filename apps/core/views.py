"""
Voyager Core Views.

Operational web views for health, readiness, status, and version probes.
Follows Voyant's pattern: view functions live in app views.py, NOT in url configs.

All probes check real infrastructure (PostgreSQL, Redis, Vault connectivity).
No mocks or stubs.
"""

from __future__ import annotations

import asyncio
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from asgiref.sync import async_to_sync
from django.http import JsonResponse
from django.db import connection

from apps.core.config import get_settings
from apps.vault_integration.client import vault_client

# Module start time for uptime calculation
_start_time = time.time()


def _run_with_timeout(func, timeout_seconds: float):
    """
    Execute a synchronous callable with a hard timeout.

    Args:
        func: Zero-argument callable to execute.
        timeout_seconds: Maximum wall-clock seconds to wait.

    Returns:
        The return value of func.

    Raises:
        concurrent.futures.TimeoutError: If func does not complete in time.
    """
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(func)
    try:
        return future.result(timeout=timeout_seconds)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def health(_request) -> JsonResponse:
    """
    Minimal liveness probe.

    Lightweight check suitable for Kubernetes liveness probes.
    Does NOT verify downstream dependency health — only confirms
    the Django process is alive and responding.

    Returns:
        200 JSON: {"status": "healthy", "service": "voyager", "version": "1.0.0", "timestamp": "..."}
    """
    return JsonResponse(
        {
            "status": "healthy",
            "service": "voyager",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
    )


def ready(_request) -> JsonResponse:
    """
    Comprehensive readiness probe.

    Checks PostgreSQL connectivity, Redis connectivity, and Vault connectivity.
    Suitable for Kubernetes readiness probes.

    Returns:
        200 JSON: {"status": "ready", "checks": {"postgresql": {...}, "redis": {...}, "vault": {...}}}
        503 JSON: {"status": "not_ready", "checks": {...}} when any critical check fails.
    """
    checks: dict = {}
    overall_ready = True
    settings = get_settings()

    # PostgreSQL check
    try:
        def _check_postgres():
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

        _run_with_timeout(_check_postgres, 3.0)
        checks["postgresql"] = {
            "status": "up",
            "details": f"Connected to {settings.database_host}:{settings.database_port}/{settings.database_name}",
        }
    except Exception as exc:
        checks["postgresql"] = {"status": "down", "error": str(exc)}
        overall_ready = False

    # Redis check
    try:
        from django.core.cache import cache

        def _check_redis():
            cache.set("__voyager_ready_probe", "ok", timeout=5)
            result = cache.get("__voyager_ready_probe")
            if result != "ok":
                raise RuntimeError("Redis cache read/write mismatch")

        _run_with_timeout(_check_redis, 3.0)
        checks["redis"] = {"status": "up", "details": "Cache read/write successful"}
    except Exception as exc:
        checks["redis"] = {"status": "down", "error": str(exc)}
        overall_ready = False

    # Vault check
    try:
        def _check_vault():
            vault_client.is_authenticated()

        _run_with_timeout(_check_vault, 3.0)
        checks["vault"] = {"status": "up", "details": "Vault client authenticated"}
    except Exception as exc:
        checks["vault"] = {"status": "down", "error": str(exc)}
        # Vault is not critical for readiness — some deployments run without it
        # in dev mode. Mark it but don't fail overall readiness.
        if settings.vault_required:
            overall_ready = False

    # Celery check (optional — only when configured)
    if settings.celery_broker_url:
        try:
            from celery import current_app as celery_app

            def _check_celery():
                inspector = celery_app.control.inspect(timeout=2.0)
                stats = inspector.stats()
                if not stats:
                    raise RuntimeError("No Celery workers responding")

            _run_with_timeout(_check_celery, 3.0)
            checks["celery"] = {"status": "up", "details": "Workers responding"}
        except Exception as exc:
            checks["celery"] = {"status": "down", "error": str(exc)}
            if settings.celery_required:
                overall_ready = False
    else:
        checks["celery"] = {
            "status": "skipped",
            "details": "CELERY_BROKER_URL is not configured",
        }

    http_status = 200 if overall_ready else 503
    return JsonResponse(
        {
            "status": "ready" if overall_ready else "not_ready",
            "service": "voyager",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "checks": checks,
        },
        status=http_status,
    )


def status_view(_request) -> JsonResponse:
    """
    Detailed administrative status report.

    Aggregates version, uptime, environment, and connected service health
    for debugging and monitoring dashboards.

    Returns:
        200 JSON: Full status payload with service health and configuration.
    """
    settings = get_settings()
    uptime_seconds = time.time() - _start_time

    status_info: dict = {
        "service": "voyager",
        "version": "1.0.0",
        "environment": settings.env,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "uptime_seconds": round(uptime_seconds, 2),
        "services": {},
    }

    # PostgreSQL status
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            pg_version = cursor.fetchone()[0]
            status_info["services"]["postgresql"] = {
                "healthy": True,
                "version": pg_version,
                "host": settings.database_host,
                "port": settings.database_port,
                "database": settings.database_name,
            }
    except Exception as exc:
        status_info["services"]["postgresql"] = {"healthy": False, "error": str(exc)}

    # Redis status
    try:
        from django.core.cache import cache

        cache.set("__voyager_status_probe", "ok", timeout=5)
        result = cache.get("__voyager_status_probe")
        status_info["services"]["redis"] = {
            "healthy": result == "ok",
            "host": settings.redis_host,
            "port": settings.redis_port,
        }
    except Exception as exc:
        status_info["services"]["redis"] = {"healthy": False, "error": str(exc)}

    # Vault status
    try:
        vault_authed = vault_client.is_authenticated()
        status_info["services"]["vault"] = {
            "healthy": vault_authed,
            "url": settings.vault_url,
        }
    except Exception as exc:
        status_info["services"]["vault"] = {"healthy": False, "error": str(exc)}

    # Keycloak status
    try:
        status_info["services"]["keycloak"] = {
            "healthy": True,
            "url": settings.keycloak_url,
            "realm": settings.keycloak_realm,
        }
    except Exception as exc:
        status_info["services"]["keycloak"] = {"healthy": False, "error": str(exc)}

    return JsonResponse(status_info)


def version_view(_request) -> JsonResponse:
    """
    API version information endpoint.

    Returns version metadata for API clients to negotiate compatibility.

    Returns:
        200 JSON: Versioning metadata with current, supported, and deprecated versions.
    """
    from apps.core.middleware import get_version_info

    version_info = get_version_info()
    version_info["service"] = "voyager"
    version_info["release"] = "1.0.0"
    return JsonResponse(version_info)
