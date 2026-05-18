"""Connection health monitoring: probes, checks, alerting.

Periodically probes platform connections for availability and latency,
records health snapshots, and provides alerting hooks.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from apps.integrations.models import PlatformConnection, PlatformHealth

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Health check endpoints per platform
# ---------------------------------------------------------------------------

_HEALTH_ENDPOINTS: dict[str, dict[str, Any]] = {
    "facebook": {
        "url": "https://graph.facebook.com/v18.0/me",
        "method": "GET",
        "auth_param": "access_token",
    },
    "instagram": {
        "url": "https://graph.facebook.com/v18.0/me",
        "method": "GET",
        "auth_param": "access_token",
    },
    "twitter": {
        "url": "https://api.twitter.com/2/users/me",
        "method": "GET",
        "auth_header": True,
    },
    "linkedin": {
        "url": "https://api.linkedin.com/v2/me",
        "method": "GET",
        "auth_header": True,
    },
    "tiktok": {
        "url": "https://open.tiktokapis.com/v2/user/info/?fields=open_id",
        "method": "GET",
        "auth_header": True,
    },
    "youtube": {
        "url": "https://www.googleapis.com/youtube/v3/channels?part=id&mine=true&maxResults=1",
        "method": "GET",
        "auth_header": True,
    },
    "google_ads": {
        "url": "https://googleads.googleapis.com/v14/customers:listAccessibleCustomers",
        "method": "GET",
        "auth_header": True,
    },
    "google_analytics": {
        "url": "https://analyticsdata.googleapis.com/v1beta/properties",
        "method": "GET",
        "auth_header": True,
    },
    "google_search_console": {
        "url": "https://www.googleapis.com/webmasters/v3/sites",
        "method": "GET",
        "auth_header": True,
    },
    "google_drive": {
        "url": "https://www.googleapis.com/drive/v3/about?fields=user",
        "method": "GET",
        "auth_header": True,
    },
    "pinterest": {
        "url": "https://api.pinterest.com/v5/user_account",
        "method": "GET",
        "auth_header": True,
    },
    "reddit": {
        "url": "https://oauth.reddit.com/api/v1/me",
        "method": "GET",
        "auth_header": True,
    },
    "snapchat": {
        "url": "https://adsapi.snapchat.com/v1/me",
        "method": "GET",
        "auth_header": True,
    },
    "slack": {
        "url": "https://slack.com/api/auth.test",
        "method": "POST",
        "auth_param": "token",
    },
    "hubspot_crm": {
        "url": "https://api.hubapi.com/integrations/v1/me",
        "method": "GET",
        "auth_header": True,
    },
    "hubspot_email": {
        "url": "https://api.hubapi.com/integrations/v1/me",
        "method": "GET",
        "auth_header": True,
    },
    "salesforce": {
        "url": "https://login.salesforce.com/services/oauth2/userinfo",
        "method": "GET",
        "auth_header": True,
    },
    "mailchimp": {
        "url": "https://{dc}.api.mailchimp.com/3.0/",
        "method": "GET",
        "auth_header": True,
        "dc_required": True,
    },
    "stripe": {
        "url": "https://api.stripe.com/v1/account",
        "method": "GET",
        "auth_header": True,
        "auth_prefix": "Bearer",
    },
    "discord": {
        "url": "https://discord.com/api/v10/users/@me",
        "method": "GET",
        "auth_header": True,
    },
    "jira": {
        "url": "https://api.atlassian.com/me",
        "method": "GET",
        "auth_header": True,
    },
    "shopify": {
        "url": "https://{shop}.myshopify.com/admin/api/2024-01/shop.json",
        "method": "GET",
        "auth_header": True,
    },
    "paypal": {
        "url": "https://api.paypal.com/v1/identity/oauth2/userinfo?schema=paypalv1.1",
        "method": "GET",
        "auth_header": True,
    },
    "asana": {
        "url": "https://app.asana.com/api/1.0/users/me",
        "method": "GET",
        "auth_header": True,
    },
    "trello": {
        "url": "https://api.trello.com/1/members/me",
        "method": "GET",
        "auth_param": "key",
    },
    "notion": {
        "url": "https://api.notion.com/v1/users/me",
        "method": "GET",
        "auth_header": True,
    },
    "monday": {
        "url": "https://api.monday.com/v2",
        "method": "POST",
        "auth_header": True,
    },
    "dropbox": {
        "url": "https://api.dropboxapi.com/2/users/get_current_account",
        "method": "POST",
        "auth_header": True,
    },
    "figma": {
        "url": "https://api.figma.com/v1/me",
        "method": "GET",
        "auth_header": True,
    },
}


# ---------------------------------------------------------------------------
# Health check execution
# ---------------------------------------------------------------------------


def check_connection_health(connection: PlatformConnection) -> PlatformHealth:
    """Probe a single platform connection and record the result.

    Makes a lightweight API call to the platform to measure availability
    and latency, then creates or updates a PlatformHealth record.

    Args:
        connection: The PlatformConnection to check.

    Returns:
        The created PlatformHealth record.
    """
    platform = connection.platform
    health_cfg = _HEALTH_ENDPOINTS.get(platform)

    if not health_cfg:
        return PlatformHealth.objects.create(
            connection=connection,
            status=PlatformHealth.Status.UNKNOWN,
            error_message=f"No health check configured for {platform}",
        )

    start_time = time.monotonic()
    latency_ms: int | None = None
    status_result = PlatformHealth.Status.HEALTHY
    error_msg = ""
    details: dict[str, Any] = {}

    try:
        access_token = connection.access_token
        if not access_token:
            status_result = PlatformHealth.Status.DOWN
            error_msg = "No access token available"
        else:
            url = str(health_cfg["url"])
            headers: dict[str, str] = {}
            params: dict[str, str] = {}

            if health_cfg.get("dc_required"):
                # Mailchimp requires datacenter from API key
                api_key = connection.api_key or ""
                dc = api_key.split("-")[-1] if "-" in api_key else "us1"
                url = url.format(dc=dc)

            if health_cfg.get("auth_header"):
                prefix = health_cfg.get("auth_prefix", "Bearer")
                headers["Authorization"] = f"{prefix} {access_token}"
            elif health_cfg.get("auth_param") == "access_token":
                params["access_token"] = access_token
            elif health_cfg.get("auth_param") == "token":
                params["token"] = access_token
            elif health_cfg.get("auth_param") == "key":
                params["key"] = access_token

            method = health_cfg.get("method", "GET")

            if method == "POST":
                resp = httpx.post(url, headers=headers, params=params, timeout=15.0)
            else:
                resp = httpx.get(url, headers=headers, params=params, timeout=15.0)

            latency_ms = int((time.monotonic() - start_time) * 1000)

            if resp.status_code == 200:
                status_result = PlatformHealth.Status.HEALTHY
                details = {"status_code": resp.status_code, "latency_ms": latency_ms}
            elif resp.status_code in (401, 403):
                status_result = PlatformHealth.Status.DEGRADED
                error_msg = f"Authentication issue: {resp.status_code}"
                details = {"status_code": resp.status_code}
            elif resp.status_code >= 500:
                status_result = PlatformHealth.Status.DEGRADED
                error_msg = f"Server error: {resp.status_code}"
                details = {"status_code": resp.status_code}
            else:
                status_result = PlatformHealth.Status.DEGRADED
                error_msg = f"Unexpected status: {resp.status_code}"
                details = {"status_code": resp.status_code}

    except httpx.TimeoutException:
        latency_ms = int((time.monotonic() - start_time) * 1000)
        status_result = PlatformHealth.Status.DOWN
        error_msg = "Request timed out"
        details = {"timeout": True}
    except httpx.RequestError as exc:
        latency_ms = int((time.monotonic() - start_time) * 1000)
        status_result = PlatformHealth.Status.DOWN
        error_msg = f"Request error: {exc}"
        details = {"error_type": type(exc).__name__}
    except Exception as exc:
        latency_ms = int((time.monotonic() - start_time) * 1000)
        status_result = PlatformHealth.Status.DOWN
        error_msg = f"Unexpected error: {exc}"
        details = {"error_type": type(exc).__name__}

    health = PlatformHealth.objects.create(
        connection=connection,
        status=status_result,
        latency_ms=latency_ms,
        error_message=error_msg,
        details_json=details,
    )

    # Update connection status based on health check
    if status_result == PlatformHealth.Status.DOWN:
        connection.status = PlatformConnection.Status.ERROR
        connection.last_error = error_msg
        connection.save(update_fields=["status", "last_error", "updated_at"])
    elif (
        status_result == PlatformHealth.Status.HEALTHY
        and connection.status == PlatformConnection.Status.ERROR
    ):
        connection.status = PlatformConnection.Status.ACTIVE
        connection.last_error = ""
        connection.save(update_fields=["status", "last_error", "updated_at"])

    return health


def check_all_connections(tenant_id: str | None = None) -> dict[str, Any]:
    """Run health checks for all active connections.

    Args:
        tenant_id: Optional tenant filter.

    Returns:
        Dictionary with ``total``, ``healthy``, ``degraded``, ``down``,
        and ``checks`` list.
    """
    qs = PlatformConnection.objects.filter(
        status__in=(PlatformConnection.Status.ACTIVE, PlatformConnection.Status.ERROR)
    )
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)

    total = 0
    healthy = 0
    degraded = 0
    down = 0
    checks: list[dict[str, Any]] = []

    for connection in qs:
        total += 1
        try:
            health = check_connection_health(connection)
            if health.status == PlatformHealth.Status.HEALTHY:
                healthy += 1
            elif health.status == PlatformHealth.Status.DEGRADED:
                degraded += 1
            else:
                down += 1

            checks.append(
                {
                    "connection_id": str(connection.id),
                    "platform": connection.platform,
                    "status": health.status,
                    "latency_ms": health.latency_ms,
                    "error": health.error_message,
                }
            )
        except Exception as exc:
            down += 1
            checks.append(
                {
                    "connection_id": str(connection.id),
                    "platform": connection.platform,
                    "status": "error",
                    "error": str(exc),
                }
            )

    return {
        "total": total,
        "healthy": healthy,
        "degraded": degraded,
        "down": down,
        "checks": checks,
    }


def get_connection_health_summary(connection_id: str, limit: int = 24) -> dict[str, Any]:
    """Get a health summary for a single connection.

    Returns the latest health check plus a trend of the last N checks.

    Args:
        connection_id: The connection UUID.
        limit: Number of historical checks to include.

    Returns:
        Dictionary with ``latest`` and ``history``.
    """
    checks = PlatformHealth.objects.filter(connection_id=connection_id).order_by("-last_check_at")[
        :limit
    ]

    if not checks:
        return {"latest": None, "history": []}

    latest = checks[0]
    history = [
        {
            "status": c.status,
            "latency_ms": c.latency_ms,
            "error": c.error_message,
            "checked_at": c.last_check_at.isoformat() if c.last_check_at else None,
        }
        for c in checks
    ]

    return {
        "latest": {
            "status": latest.status,
            "latency_ms": latest.latency_ms,
            "error": latest.error_message,
            "details": latest.details_json,
            "checked_at": latest.last_check_at.isoformat() if latest.last_check_at else None,
        },
        "history": history,
    }
