"""
Voyager Configuration.

Pydantic-settings based configuration following Voyant's pattern.
Uses VOYAGER_ prefix for all environment variables.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional


def _get_bool_env(key: str, default: bool = False) -> bool:
    """Parse a boolean from an environment variable."""
    value = os.environ.get(key, "").lower()
    return value in ("1", "true", "yes", "on") if value else default


class VoyagerSettings:
    """
    Voyager application settings.

    Loads from environment variables with VOYAGER_ prefix.
    Follows the same pattern as Voyant's settings.
    """

    # ------------------------------------------------------------------
    # Environment
    # ------------------------------------------------------------------
    @property
    def env(self) -> str:
        return os.environ.get("VOYAGER_ENV", "development")

    # ------------------------------------------------------------------
    # Database (PostgreSQL)
    # ------------------------------------------------------------------
    @property
    def database_host(self) -> str:
        return os.environ.get("VOYAGER_DATABASE_HOST", "localhost")

    @property
    def database_port(self) -> int:
        return int(os.environ.get("VOYAGER_DATABASE_PORT", "5432"))

    @property
    def database_name(self) -> str:
        return os.environ.get("VOYAGER_DATABASE_NAME", "voyager")

    @property
    def database_url(self) -> str:
        return os.environ.get(
            "DATABASE_URL",
            f"postgresql://voyager:voyager@{self.database_host}:{self.database_port}/{self.database_name}",
        )

    # ------------------------------------------------------------------
    # Redis
    # ------------------------------------------------------------------
    @property
    def redis_host(self) -> str:
        return os.environ.get("VOYAGER_REDIS_HOST", "localhost")

    @property
    def redis_port(self) -> int:
        return int(os.environ.get("VOYAGER_REDIS_PORT", "6379"))

    @property
    def redis_url(self) -> str:
        return os.environ.get(
            "REDIS_URL",
            f"redis://{self.redis_host}:{self.redis_port}/0",
        )

    # ------------------------------------------------------------------
    # Vault
    # ------------------------------------------------------------------
    @property
    def vault_url(self) -> str:
        return os.environ.get("VAULT_ADDR", "http://localhost:8200")

    @property
    def vault_token(self) -> str:
        return os.environ.get("VAULT_TOKEN", "dev-root-token")

    @property
    def vault_required(self) -> bool:
        return _get_bool_env("VOYAGER_VAULT_REQUIRED", default=False)

    # ------------------------------------------------------------------
    # Keycloak
    # ------------------------------------------------------------------
    @property
    def keycloak_url(self) -> str:
        return os.environ.get("KEYCLOAK_URL", "http://localhost:8080")

    @property
    def keycloak_realm(self) -> str:
        return os.environ.get("KEYCLOAK_REALM", "voyager")

    @property
    def keycloak_client_id(self) -> str:
        return os.environ.get("KEYCLOAK_CLIENT_ID", "voyager-api")

    @property
    def keycloak_client_secret(self) -> str:
        return os.environ.get("KEYCLOAK_CLIENT_SECRET", "")

    # ------------------------------------------------------------------
    # Celery
    # ------------------------------------------------------------------
    @property
    def celery_broker_url(self) -> str:
        return os.environ.get("CELERY_BROKER_URL", self.redis_url)

    @property
    def celery_required(self) -> bool:
        return _get_bool_env("VOYAGER_CELERY_REQUIRED", default=False)


@lru_cache(maxsize=1)
def get_settings() -> VoyagerSettings:
    """Return the cached settings singleton."""
    return VoyagerSettings()
