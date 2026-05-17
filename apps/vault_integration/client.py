"""
HashiCorp Vault client for Voyager secrets management.

Provides a typed interface to HashiCorp Vault via the ``hvac`` library.
All secrets are stored under the ``voyager/`` mount point (distinct from
Voyant's mount point). Supports KV v2 secrets, dynamic database credentials,
platform API tokens, and AI provider API keys.

Usage:
    ```python
    from apps.vault_integration.client import vault_client

    # Read a secret
    db_password = vault_client.get_secret("database/voyager", "password")

    # Write a secret
    vault_client.put_secret("api-keys/stripe", {"key": "sk_live_..."})

    # Get dynamic DB credentials
    creds = vault_client.get_database_credentials("voyager")
    ```
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Union

import hvac
from hvac.exceptions import VaultError

from apps.core.config import get_settings

logger = logging.getLogger(__name__)


class VaultClient:
    """HashiCorp Vault client for Voyager secrets.

    Manages connection lifecycle, secret CRUD operations, and dynamic
    credential retrieval. Uses the ``voyager/`` mount point for all
    secret paths to ensure isolation from other applications.

    Attributes:
        client: The underlying ``hvac.Client`` instance.
        mount_point: The Vault KV mount point (default ``"voyager"``).
        _connected: Internal connectivity cache.
    """

    # Default mount point for Voyager secrets (NOT "voyant")
    DEFAULT_MOUNT_POINT: str = "voyager"

    # Standard secret paths
    PATH_DATABASE: str = "database"
    PATH_API_KEYS: str = "api-keys"
    PATH_PLATFORM_TOKENS: str = "platform-tokens"
    PATH_AI_KEYS: str = "ai-providers"
    PATH_SSL_CERTS: str = "ssl"
    PATH_SMS_GATEWAY: str = "sms-gateway"

    def __init__(self) -> None:
        """Initialise the Vault client from Voyager settings.

        Reads ``secrets_vault_url`` and ``secrets_vault_token`` from
        pydantic-settings via ``get_settings()``.
        """
        settings = get_settings()
        self._vault_url = settings.secrets_vault_url or "http://vault:8200"
        self._vault_token = settings.secrets_vault_token or ""
        self.mount_point = settings.secrets_vault_mount_point or self.DEFAULT_MOUNT_POINT
        self._connected = False

        self.client = hvac.Client(url=self._vault_url, token=self._vault_token)
        if self._vault_token:
            self._connected = self.client.is_authenticated()

    # -- connection -----------------------------------------------------------

    def is_authenticated(self) -> bool:
        """Check if the Vault client is authenticated and reachable.

        Returns:
            ``True`` if the client has a valid token and can connect.
        """
        if not self._vault_token:
            return False
        try:
            return self.client.is_authenticated()
        except Exception as exc:
            logger.debug("Vault authentication check failed: %s", exc)
            return False

    def reauthenticate(self, token: Optional[str] = None) -> bool:
        """Re-authenticate with a new or existing token.

        Args:
            token: New Vault token. If ``None``, re-uses the current token.

        Returns:
            ``True`` if authentication succeeded.
        """
        if token:
            self._vault_token = token
            self.client.token = token
        try:
            self._connected = self.client.is_authenticated()
            return self._connected
        except Exception as exc:
            logger.error("Vault re-authentication failed: %s", exc)
            self._connected = False
            return False

    # -- KV v2 secret operations ----------------------------------------------

    def get_secret(self, path: str, key: Optional[str] = None) -> Union[str, Dict[str, Any]]:
        """Read a secret from Vault KV v2.

        Args:
            path: Secret path relative to the mount point
                (e.g. ``"database/voyager"``).
            key: Optional specific key to extract from the secret data.
                If ``None``, returns the full data dictionary.

        Returns:
            The secret value (string if key specified, dict otherwise).

        Raises:
            VaultError: If the secret does not exist or Vault is unreachable.
            ValueError: If the key is not found in the secret.
        """
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=self.mount_point,
            )
            data = response["data"]["data"]

            if key is not None:
                if key not in data:
                    raise ValueError(
                        f"Key '{key}' not found in secret at {path}"
                    )
                return str(data[key])

            return dict(data)

        except VaultError as exc:
            logger.error(
                "Failed to read secret at %s/%s: %s", self.mount_point, path, exc
            )
            raise

    def put_secret(self, path: str, data: Dict[str, Any]) -> bool:
        """Write or update a secret in Vault KV v2.

        Args:
            path: Secret path relative to the mount point.
            data: Dictionary of key-value pairs to store.

        Returns:
            ``True`` if the secret was written successfully.

        Raises:
            VaultError: If the write fails.
        """
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret=data,
                mount_point=self.mount_point,
            )
            logger.info("Secret written at %s/%s", self.mount_point, path)
            return True

        except VaultError as exc:
            logger.error(
                "Failed to write secret at %s/%s: %s", self.mount_point, path, exc
            )
            raise

    def delete_secret(self, path: str) -> bool:
        """Delete a secret from Vault KV v2.

        Args:
            path: Secret path relative to the mount point.

        Returns:
            ``True`` if the secret was deleted.

        Raises:
            VaultError: If deletion fails.
        """
        try:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=path,
                mount_point=self.mount_point,
            )
            logger.info("Secret deleted at %s/%s", self.mount_point, path)
            return True

        except VaultError as exc:
            logger.error(
                "Failed to delete secret at %s/%s: %s", self.mount_point, path, exc
            )
            raise

    def list_secrets(self, path: str = "") -> list[str]:
        """List secret keys at a given path.

        Args:
            path: Path prefix to list (e.g. ``"database/"``).

        Returns:
            List of secret key names.

        Raises:
            VaultError: If listing fails.
        """
        try:
            response = self.client.secrets.kv.v2.list_secrets(
                path=path,
                mount_point=self.mount_point,
            )
            return response["data"]["keys"]

        except VaultError as exc:
            logger.error(
                "Failed to list secrets at %s/%s: %s", self.mount_point, path, exc
            )
            raise

    # -- dynamic database credentials -----------------------------------------

    def get_database_credentials(self, db_name: str = "voyager") -> Dict[str, str]:
        """Retrieve dynamic database credentials from Vault's database engine.

        Args:
            db_name: Name of the database connection configured in Vault
                (default ``"voyager"``).

        Returns:
            Dictionary with ``username`` and ``password`` keys.

        Raises:
            VaultError: If credential generation fails.
        """
        try:
            response = self.client.secrets.database.generate_credentials(
                name=db_name,
            )
            data = response["data"]
            creds = {
                "username": data["username"],
                "password": data["password"],
                "lease_id": response.get("lease_id", ""),
                "lease_duration": response.get("lease_duration", 0),
                "renewable": response.get("renewable", False),
            }
            logger.info(
                "Generated dynamic DB credentials for '%s' (user: %s)",
                db_name,
                creds["username"],
            )
            return creds

        except VaultError as exc:
            logger.error(
                "Failed to generate DB credentials for '%s': %s", db_name, exc
            )
            raise

    def rotate_database_credentials(self, db_name: str = "voyager") -> Dict[str, Any]:
        """Rotate the static database credentials stored in Vault.

        Args:
            db_name: Name of the database connection.

        Returns:
            Response data from the rotation operation.

        Raises:
            VaultError: If rotation fails.
        """
        try:
            response = self.client.secrets.database.rotate_static_credentials(
                name=db_name,
            )
            logger.info("Rotated static DB credentials for '%s'", db_name)
            return response

        except VaultError as exc:
            logger.error(
                "Failed to rotate DB credentials for '%s': %s", db_name, exc
            )
            raise

    # -- platform API tokens --------------------------------------------------

    def get_platform_token(self, platform: str) -> str:
        """Retrieve an API token for a social media or ad platform.

        Args:
            platform: Platform name (e.g. ``"facebook"``, ``"twitter"``,
                ``"linkedin"``, ``"google_ads"``).

        Returns:
            The API token string.

        Raises:
            VaultError: If the token is not found.
            ValueError: If platform name is empty.
        """
        if not platform:
            raise ValueError("Platform name is required")

        path = f"{self.PATH_PLATFORM_TOKENS}/{platform.lower()}"
        return str(self.get_secret(path, "token"))

    def put_platform_token(self, platform: str, token: str) -> bool:
        """Store an API token for a platform.

        Args:
            platform: Platform name.
            token: The API token string.

        Returns:
            ``True`` if stored successfully.
        """
        path = f"{self.PATH_PLATFORM_TOKENS}/{platform.lower()}"
        return self.put_secret(path, {"token": token})

    # -- AI provider API keys -------------------------------------------------

    def get_ai_api_key(self, provider: str) -> str:
        """Retrieve an API key for an AI/LLM provider.

        Args:
            provider: Provider name (e.g. ``"openai"``, ``"anthropic"``,
                ``"google"``, ``"cohere"``).

        Returns:
            The API key string.

        Raises:
            VaultError: If the key is not found.
            ValueError: If provider name is empty.
        """
        if not provider:
            raise ValueError("Provider name is required")

        path = f"{self.PATH_AI_KEYS}/{provider.lower()}"
        return str(self.get_secret(path, "api_key"))

    def put_ai_api_key(self, provider: str, api_key: str) -> bool:
        """Store an API key for an AI provider.

        Args:
            provider: Provider name.
            api_key: The API key string.

        Returns:
            ``True`` if stored successfully.
        """
        path = f"{self.PATH_AI_KEYS}/{provider.lower()}"
        return self.put_secret(path, {"api_key": api_key})

    # -- generic API keys -----------------------------------------------------

    def get_api_key(self, service: str, key_name: str = "api_key") -> str:
        """Retrieve an API key for any service.

        Args:
            service: Service name (e.g. ``"stripe"``, ``"sendgrid"``).
            key_name: The key field name within the secret.

        Returns:
            The API key string.
        """
        path = f"{self.PATH_API_KEYS}/{service.lower()}"
        return str(self.get_secret(path, key_name))

    def put_api_key(self, service: str, key_value: str, key_name: str = "api_key") -> bool:
        """Store an API key for a service.

        Args:
            service: Service name.
            key_value: The API key value.
            key_name: The field name for the key.

        Returns:
            ``True`` if stored successfully.
        """
        path = f"{self.PATH_API_KEYS}/{service.lower()}"
        return self.put_secret(path, {key_name: key_value})

    # -- SSL / TLS certificates -----------------------------------------------

    def get_certificate(self, cert_name: str) -> Dict[str, str]:
        """Retrieve an SSL/TLS certificate bundle.

        Args:
            cert_name: Certificate name (e.g. ``"wildcard"``).

        Returns:
            Dictionary with ``cert`` and ``key`` keys.
        """
        path = f"{self.PATH_SSL_CERTS}/{cert_name}"
        data = self.get_secret(path)
        if isinstance(data, dict):
            return {
                "cert": data.get("cert", ""),
                "key": data.get("key", ""),
                "chain": data.get("chain", ""),
            }
        raise ValueError(f"Invalid certificate data at {path}")

    # -- SMS gateway credentials ----------------------------------------------

    def get_sms_credentials(self, gateway: str = "twilio") -> Dict[str, str]:
        """Retrieve SMS gateway credentials.

        Args:
            gateway: Gateway name (default ``"twilio"``).

        Returns:
            Dictionary with ``account_sid`` and ``auth_token`` keys.
        """
        path = f"{self.PATH_SMS_GATEWAY}/{gateway.lower()}"
        data = self.get_secret(path)
        if isinstance(data, dict):
            return {
                "account_sid": data.get("account_sid", ""),
                "auth_token": data.get("auth_token", ""),
                "from_number": data.get("from_number", ""),
            }
        raise ValueError(f"Invalid SMS credentials at {path}")

    # -- lease management -----------------------------------------------------

    def renew_lease(self, lease_id: str, increment: Optional[int] = None) -> Dict[str, Any]:
        """Renew a Vault lease for dynamic secrets.

        Args:
            lease_id: The lease ID to renew.
            increment: Optional lease increment in seconds.

        Returns:
            Renewal response data.
        """
        try:
            response = self.client.sys.renew_lease(
                lease_id=lease_id,
                increment=increment,
            )
            return response

        except VaultError as exc:
            logger.error("Failed to renew lease %s: %s", lease_id, exc)
            raise

    def revoke_lease(self, lease_id: str) -> bool:
        """Revoke a Vault lease.

        Args:
            lease_id: The lease ID to revoke.

        Returns:
            ``True`` if revoked successfully.
        """
        try:
            self.client.sys.revoke_lease(lease_id=lease_id)
            logger.info("Revoked lease %s", lease_id)
            return True

        except VaultError as exc:
            logger.error("Failed to revoke lease %s: %s", lease_id, exc)
            raise


# Singleton instance for application-wide use
vault_client = VaultClient()
