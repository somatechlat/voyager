"""VoyagerKeycloakAuth — JWT validator and user builder for Voyager."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from ninja.errors import HttpError

from apps.core.config import get_settings

from .user import VOYAGER_ROLE_PREFIX, VOYAGER_SUPERADMIN, VoyagerUser

logger = logging.getLogger(__name__)


class VoyagerKeycloakAuth:
    """JWT validator and user builder for Voyager, extending Voyant's pattern.

    Fetches and caches the Keycloak JWKS, validates RS256 token signatures,
    extracts claims, and derives Voyager-specific permissions from role
    assignments. Supports both realm roles and resource_access roles.

    Role to permission mapping covers all Voyager marketing platform roles
    from super-admin down to read-only guest access.
    """

    # -- Voyager role -> permission mapping ----------------------------------

    VOYAGER_ROLE_MAP: dict[str, list[str]] = {
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
        self._jwks: dict[str, Any] | None = None
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
        self._jwks_url = f"{self._server_url}/realms/{self._realm}/protocol/openid-connect/certs"
        self._issuer = f"{self._server_url}/realms/{self._realm}"

    # -- JWKS ----------------------------------------------------------------

    def _get_jwks(self) -> dict[str, Any]:
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
            key: dict[str, Any] | None = None
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

    def _extract_roles(self, payload: dict[str, Any]) -> list[str]:
        """Aggregate roles from ``realm_access`` and ``resource_access``.

        Args:
            payload: Decoded JWT payload dictionary.

        Returns:
            Flat list of all role names assigned to the user.
        """
        roles: list[str] = []

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

    def _extract_workspace_roles(self, payload: dict[str, Any]) -> dict[str, list[str]]:
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

    def _derive_permissions(self, roles: list[str]) -> list[str]:
        """Derive granular Voyager permissions from assigned roles.

        Args:
            roles: List of role names from the JWT.

        Returns:
            Deduplicated list of permission strings.
        """
        permissions: list[str] = []
        for role in roles:
            if role in self.VOYAGER_ROLE_MAP:
                permissions.extend(self.VOYAGER_ROLE_MAP[role])
        return list(set(permissions))

    def get_role_permissions(self, role: str) -> list[str]:
        """Look up the permission set for a specific Voyager role.

        Args:
            role: Role name to look up.

        Returns:
            List of permission strings for the role, empty if unknown.
        """
        return list(self.VOYAGER_ROLE_MAP.get(role, []))

    def list_defined_roles(self) -> list[str]:
        """Return all Voyager roles defined in the role map.

        Returns:
            Sorted list of role name strings.
        """
        return sorted(self.VOYAGER_ROLE_MAP.keys())

    def list_defined_permissions(self) -> list[str]:
        """Return all unique permissions across all defined roles.

        Returns:
            Sorted deduplicated list of permission strings.
        """
        perms: set[str] = set()
        for role_perms in self.VOYAGER_ROLE_MAP.values():
            perms.update(role_perms)
        return sorted(perms)
