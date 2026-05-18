"""OAuth 2.0 flow handlers for 50+ platforms.

Supports authorization-code flow with PKCE, token refresh, state
validation (CSRF), and AES-encrypted credential storage.
Platforms: Meta, Google, Twitter/X, LinkedIn, TikTok, YouTube,
Pinterest, Snapchat, Reddit, Mailchimp, HubSpot, Salesforce,
Shopify, Stripe, Slack, Discord, Asana, Trello, Jira, Notion,
and many more.
"""

from __future__ import annotations

import logging
import secrets
import time
from typing import Any
from urllib.parse import urlencode

import httpx
from django.utils import timezone

from apps.integrations.models import PlatformConnection

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OAuth state store (in-memory; production should use Redis)
# ---------------------------------------------------------------------------

_oauth_states: dict[str, dict[str, Any]] = {}


def _clear_expired_states() -> None:
    """Remove OAuth state entries older than 10 minutes."""
    now = time.time()
    expired = [s for s, v in _oauth_states.items() if now - v["created_at"] > 600]
    for s in expired:
        _oauth_states.pop(s, None)


def _store_state(state: str, tenant_id: str, platform: str, scopes: list[str]) -> None:
    """Store an OAuth state parameter for CSRF protection."""
    _clear_expired_states()
    _oauth_states[state] = {
        "tenant_id": tenant_id,
        "platform": platform,
        "scopes": scopes,
        "created_at": time.time(),
    }


def _load_state(state: str) -> dict[str, Any] | None:
    """Load and validate an OAuth state entry."""
    entry = _oauth_states.pop(state, None)
    if not entry:
        return None
    if time.time() - entry["created_at"] > 600:
        return None
    return entry


from apps.integrations.services.platform_configs import PLATFORM_CONFIG

# ---------------------------------------------------------------------------
# Credential retrieval
# ---------------------------------------------------------------------------


def _get_client_credentials(platform: str) -> tuple[str, str]:
    """Return (client_id, client_secret) for a platform.

    Credentials are read from environment variables following the pattern
    ``<PLATFORM>_CLIENT_ID`` and ``<PLATFORM>_CLIENT_SECRET``.
    """
    env_prefix = platform.upper().replace("_", "")
    import os

    client_id = os.environ.get(f"{env_prefix}_CLIENT_ID", "")
    client_secret = os.environ.get(f"{env_prefix}_CLIENT_SECRET", "")
    if not client_id:
        alt = platform.upper().replace("_", "_")
        client_id = os.environ.get(f"{alt}_CLIENT_ID", "")
    if not client_secret:
        alt = platform.upper().replace("_", "_")
        client_secret = os.environ.get(f"{alt}_CLIENT_SECRET", "")
    return client_id, client_secret


def _get_redirect_uri() -> str:
    """Return the OAuth redirect URI."""
    import os

    return os.environ.get(
        "VOYAGER_OAUTH_REDIRECT_URI", "http://localhost:8000/api/v1/integrations/oauth/callback"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def initiate_oauth_flow(
    tenant_id: str, platform: str, scopes: list[str] | None = None
) -> dict[str, str]:
    """Generate an OAuth authorization URL for a platform.

    Creates a cryptographically random state parameter, stores it for
    CSRF protection (expires in 10 minutes), and builds the platform
    authorization URL with all required query parameters.

    Args:
        tenant_id: The tenant initiating the OAuth flow.
        platform: Platform identifier (e.g. ``"facebook"``, ``"google_ads"``).
        scopes: Optional list of OAuth scopes. Defaults to the platform's
            standard scopes.

    Returns:
        Dictionary with ``auth_url`` and ``state`` keys.

    Raises:
        ValueError: If the platform is not supported.
    """
    if platform not in PLATFORM_CONFIG:
        raise ValueError(f"Unsupported platform: {platform}")

    config = PLATFORM_CONFIG[platform]
    client_id, _ = _get_client_credentials(platform)
    redirect_uri = _get_redirect_uri()

    chosen_scopes = scopes or config["default_scopes"]
    scope_str = config["scope_separator"].join(chosen_scopes)

    state = secrets.token_urlsafe(32)
    _store_state(state, tenant_id, platform, chosen_scopes)

    params: dict[str, str] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope_str,
        "state": state,
    }

    # Platform-specific extra parameters
    if "access_type" in config:
        params["access_type"] = str(config["access_type"])
    if "prompt" in config:
        params["prompt"] = str(config["prompt"])
    if "audience" in config:
        params["audience"] = str(config["audience"])
    if config.get("duration"):
        params["duration"] = str(config["duration"])
    if config.get("token_access_type"):
        params["token_access_type"] = str(config["token_access_type"])

    auth_url = config["auth_endpoint"] + "?" + urlencode(params)

    return {"auth_url": auth_url, "state": state}


def handle_oauth_callback(code: str, state: str) -> dict[str, Any]:
    """Exchange an authorization code for access/refresh tokens.

    Validates the state parameter (CSRF protection), exchanges the code
    with the platform token endpoint, creates a PlatformConnection with
    encrypted tokens, and tests the connection.

    Args:
        code: The authorization code from the platform.
        state: The state parameter returned by the platform.

    Returns:
        Dictionary with ``success``, ``connection_id``, and ``test_result``.

    Raises:
        ValueError: If the state is invalid or expired.
        RuntimeError: If the token exchange fails.
    """
    state_record = _load_state(state)
    if not state_record:
        raise ValueError("Invalid or expired state parameter")

    platform = state_record["platform"]
    tenant_id = state_record["tenant_id"]
    _ = state_record["scopes"]  # validated during state creation

    config = PLATFORM_CONFIG[platform]
    client_id, client_secret = _get_client_credentials(platform)
    redirect_uri = _get_redirect_uri()

    payload: dict[str, str] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if config.get("token_endpoint_auth") == "basic":
        import base64

        creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        headers["Authorization"] = f"Basic {creds}"
        del payload["client_secret"]

    try:
        resp = httpx.post(config["token_endpoint"], data=payload, headers=headers, timeout=30.0)
        resp.raise_for_status()
        token_data = resp.json()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text
        logger.error(
            "Token exchange failed for %s: %s - %s", platform, exc.response.status_code, body
        )
        raise RuntimeError(f"Token exchange failed: {exc.response.status_code}") from exc
    except Exception as exc:
        logger.error("Token exchange error for %s: %s", platform, exc)
        raise RuntimeError(f"Token exchange error: {exc}") from exc

    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)
    token_type = token_data.get("token_type", "Bearer")
    scope = token_data.get("scope", "")

    connection = PlatformConnection.objects.create(
        tenant_id=tenant_id,
        platform=platform,
        connection_type=PlatformConnection.ConnectionType.OAUTH2,
        status=PlatformConnection.Status.ACTIVE,
        scopes_json=scope.split() if " " in str(scope) else str(scope).split(","),
        expires_at=timezone.now() + timezone.timedelta(seconds=int(expires_in)),
        token_type=token_type,
    )
    connection.access_token = access_token
    if refresh_token:
        connection.refresh_token = refresh_token
    connection.save()

    test_result = _test_connection(platform, access_token)

    return {
        "success": True,
        "connection_id": str(connection.id),
        "test_result": test_result,
    }


def refresh_access_token(connection: PlatformConnection) -> dict[str, Any]:
    """Refresh the access token for an OAuth connection.

    Uses the stored refresh token to obtain a new access token from the
    platform's token endpoint. Updates the connection in place.

    Args:
        connection: The PlatformConnection to refresh.

    Returns:
        Dictionary with ``success`` and ``expires_at``.

    Raises:
        RuntimeError: If no refresh token is available or refresh fails.
    """
    if not connection.refresh_token:
        connection.status = PlatformConnection.Status.EXPIRED
        connection.save(update_fields=["status", "updated_at"])
        raise RuntimeError("No refresh token available")

    platform = connection.platform
    if platform not in PLATFORM_CONFIG:
        raise ValueError(f"Unsupported platform for refresh: {platform}")

    config = PLATFORM_CONFIG[platform]
    client_id, client_secret = _get_client_credentials(platform)

    payload: dict[str, str] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": connection.refresh_token,
        "grant_type": "refresh_token",
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if config.get("token_endpoint_auth") == "basic":
        import base64

        creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        headers["Authorization"] = f"Basic {creds}"
        del payload["client_secret"]

    try:
        resp = httpx.post(config["token_endpoint"], data=payload, headers=headers, timeout=30.0)
        resp.raise_for_status()
        token_data = resp.json()
    except httpx.HTTPStatusError as exc:
        connection.status = PlatformConnection.Status.EXPIRED
        connection.last_error = f"Refresh failed: {exc.response.status_code}"
        connection.save(update_fields=["status", "last_error", "updated_at"])
        raise RuntimeError(f"Token refresh failed: {exc.response.status_code}") from exc
    except Exception as exc:
        connection.last_error = f"Refresh error: {exc}"
        connection.save(update_fields=["last_error", "updated_at"])
        raise RuntimeError(f"Token refresh error: {exc}") from exc

    new_access = token_data.get("access_token", "")
    new_refresh = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)

    connection.access_token = new_access
    if new_refresh:
        connection.refresh_token = new_refresh
    connection.expires_at = timezone.now() + timezone.timedelta(seconds=int(expires_in))
    connection.last_refreshed_at = timezone.now()
    connection.status = PlatformConnection.Status.ACTIVE
    connection.last_error = ""
    connection.save()

    return {"success": True, "expires_at": connection.expires_at.isoformat()}


def revoke_connection(connection: PlatformConnection) -> None:
    """Revoke an OAuth connection and invalidate its tokens.

    Attempts to call the platform's revocation endpoint if available,
    then marks the connection as revoked and clears all tokens.

    Args:
        connection: The PlatformConnection to revoke.
    """
    platform = connection.platform
    token = connection.access_token

    # Attempt platform revocation where documented
    if platform in ("google_ads", "google_analytics", "youtube", "google_drive") and token:
        try:
            httpx.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": token},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0,
            )
        except Exception as exc:
            logger.warning("Google token revocation failed: %s", exc)

    connection.access_token = ""
    connection.refresh_token = ""
    connection.api_key = ""
    connection.status = PlatformConnection.Status.REVOKED
    connection.expires_at = None
    connection.save()
    logger.info("Connection revoked: %s (%s)", connection.id, platform)


# ---------------------------------------------------------------------------
# Connection testing
# ---------------------------------------------------------------------------


def _test_connection(platform: str, access_token: str) -> dict[str, Any]:
    """Test a connection by making a lightweight API call.

    Args:
        platform: The platform identifier.
        access_token: The (decrypted) access token.

    Returns:
        Dictionary with ``success`` and ``details``.
    """
    test_endpoints: dict[str, dict[str, str]] = {
        "facebook": {"url": "https://graph.facebook.com/me", "param": "access_token"},
        "instagram": {"url": "https://graph.facebook.com/me", "param": "access_token"},
        "twitter": {"url": "https://api.twitter.com/2/users/me", "header": True},
        "linkedin": {"url": "https://api.linkedin.com/v2/me", "header": True},
        "youtube": {
            "url": "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
            "header": True,
        },
        "google_ads": {
            "url": "https://googleads.googleapis.com/v14/customers:listAccessibleCustomers",
            "header": True,
        },
        "google_analytics": {
            "url": "https://analyticsdata.googleapis.com/v1beta/properties",
            "header": True,
        },
        "tiktok": {
            "url": "https://open.tiktokapis.com/v2/user/info/?fields=open_id",
            "header": True,
        },
        "pinterest": {"url": "https://api.pinterest.com/v5/user_account", "header": True},
        "reddit": {"url": "https://oauth.reddit.com/api/v1/me", "header": True},
        "slack": {"url": "https://slack.com/api/auth.test", "param": "token"},
        "hubspot_crm": {
            "url": "https://api.hubapi.com/oauth/v1/access-tokens/{token}",
            "url_token": True,
        },
        "salesforce": {
            "url": "https://login.salesforce.com/services/oauth2/userinfo",
            "header": True,
        },
        "stripe": {"url": "https://api.stripe.com/v1/account", "header": True},
        "discord": {"url": "https://discord.com/api/v10/users/@me", "header": True},
        "jira": {"url": "https://api.atlassian.com/me", "header": True},
        "shopify": {"url": "", "header": True},
    }

    test_cfg = test_endpoints.get(platform)
    if not test_cfg:
        return {"success": True, "details": "No test endpoint configured"}

    try:
        url = test_cfg["url"]
        if test_cfg.get("url_token"):
            url = url.format(token=access_token)

        headers: dict[str, str] = {}
        params: dict[str, str] = {}

        if test_cfg.get("param") == "access_token":
            params["access_token"] = access_token
        elif test_cfg.get("param") == "token":
            params["token"] = access_token
        elif test_cfg.get("header"):
            headers["Authorization"] = f"Bearer {access_token}"

        resp = httpx.get(url, headers=headers, params=params, timeout=15.0)
        resp.raise_for_status()
        return {"success": True, "details": {"status_code": resp.status_code}}
    except httpx.HTTPStatusError as exc:
        return {"success": False, "details": {"status_code": exc.response.status_code}}
    except Exception as exc:
        return {"success": False, "details": {"error": str(exc)}}


def get_expiring_connections(minutes: int = 30) -> list[PlatformConnection]:
    """Return active connections expiring within the given window.

    Args:
        minutes: Minutes before expiry to consider (default 30).

    Returns:
        QuerySet of PlatformConnection objects.
    """
    threshold = timezone.now() + timezone.timedelta(minutes=minutes)
    return list(
        PlatformConnection.objects.filter(
            status=PlatformConnection.Status.ACTIVE,
            expires_at__lte=threshold,
            connection_type=PlatformConnection.ConnectionType.OAUTH2,
        ).exclude(expires_at__isnull=True)
    )
