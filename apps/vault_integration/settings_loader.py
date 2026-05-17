"""
Settings loader for Voyager using HashiCorp Vault as the source.

Provides functions to load configuration blocks from Vault KV paths and
return them as Python dictionaries ready for Django settings injection.

All paths use the ``voyager/`` mount point for isolation from other apps.

Usage:
    ```python
    from apps.vault_integration.settings_loader import (
        load_settings_from_vault,
        get_database_config_from_vault,
    )

    db_config = get_database_config_from_vault()
    DATABASES = {"default": db_config}
    ```
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from apps.vault_integration.client import vault_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_settings_from_vault(
    path: str = "settings",
    fallback_prefix: str = "VOYAGER_",
) -> Dict[str, Any]:
    """Load a complete settings block from Vault.

    Reads all keys from ``voyager/settings`` (or the given path) and returns
    them as a flat dictionary. If Vault is unavailable, falls back to
    environment variables with the given prefix.

    Args:
        path: Vault KV path to read (default ``"settings"``).
        fallback_prefix: Environment variable prefix for fallback.

    Returns:
        Dictionary of setting key-value pairs.
    """
    try:
        data = vault_client.get_secret(path)
        if isinstance(data, dict):
            logger.info("Loaded %d settings from Vault path '%s'", len(data), path)
            return data
    except Exception as exc:
        logger.warning(
            "Failed to load settings from Vault path '%s': %s. Falling back to env vars.",
            path,
            exc,
        )

    # Fallback: collect env vars with the prefix
    return _load_from_env(fallback_prefix)


def get_database_config_from_vault(
    db_name: str = "voyager",
) -> Dict[str, Any]:
    """Load database configuration from Vault.

    Reads from ``voyager/database/<db_name>`` and returns a Django-compatible
    DATABASES dictionary entry.

    Args:
        db_name: Name of the database config in Vault.

    Returns:
        Dictionary with ENGINE, NAME, USER, PASSWORD, HOST, PORT keys.
    """
    try:
        data = vault_client.get_secret(f"database/{db_name}")
        if isinstance(data, dict):
            return _build_django_db_config(data)
    except Exception as exc:
        logger.warning(
            "Failed to load DB config from Vault for '%s': %s", db_name, exc
        )

    # Fallback: parse DATABASE_URL from environment
    db_url = os.environ.get("DATABASE_URL", os.environ.get("VOYAGER_DATABASE_URL", ""))
    if db_url:
        return _parse_database_url(db_url)

    # Final fallback: return defaults for local development
    return _default_db_config()


def get_redis_config_from_vault(
    instance: str = "default",
) -> Dict[str, Any]:
    """Load Redis configuration from Vault.

    Reads from ``voyager/redis/<instance>`` and returns Django Caches-compatible
    configuration.

    Args:
        instance: Redis instance name in Vault.

    Returns:
        Dictionary with LOCATION, OPTIONS keys.
    """
    try:
        data = vault_client.get_secret(f"redis/{instance}")
        if isinstance(data, dict):
            return {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": data.get("url", "redis://redis:6379/0"),
                "OPTIONS": {
                    "CLIENT_CLASS": "django_redis.client.DefaultClient",
                    "PASSWORD": data.get("password", ""),
                    "SSL": data.get("ssl", False),
                },
            }
    except Exception as exc:
        logger.warning(
            "Failed to load Redis config from Vault for '%s': %s", instance, exc
        )

    # Fallback
    redis_url = os.environ.get("REDIS_URL", os.environ.get("VOYAGER_REDIS_URL", "redis://redis:6379/0"))
    return {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": redis_url,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }


def get_kafka_config_from_vault(
    cluster: str = "default",
) -> Dict[str, str]:
    """Load Kafka bootstrap configuration from Vault.

    Reads from ``voyager/kafka/<cluster>``.

    Args:
        cluster: Kafka cluster name in Vault.

    Returns:
        Dictionary with bootstrap_servers, sasl_username, sasl_password.
    """
    try:
        data = vault_client.get_secret(f"kafka/{cluster}")
        if isinstance(data, dict):
            return {
                "bootstrap_servers": data.get("bootstrap_servers", ""),
                "sasl_username": data.get("sasl_username", ""),
                "sasl_password": data.get("sasl_password", ""),
                "security_protocol": data.get("security_protocol", "SASL_SSL"),
                "sasl_mechanism": data.get("sasl_mechanism", "SCRAM-SHA-256"),
            }
    except Exception as exc:
        logger.warning(
            "Failed to load Kafka config from Vault for '%s': %s", cluster, exc
        )

    # Fallback
    bootstrap = os.environ.get(
        "KAFKA_BOOTSTRAP_SERVERS",
        os.environ.get("VOYAGER_KAFKA_BOOTSTRAP_SERVERS", ""),
    )
    return {
        "bootstrap_servers": bootstrap,
        "sasl_username": "",
        "sasl_password": "",
        "security_protocol": "PLAINTEXT",
        "sasl_mechanism": "",
    }


def get_keycloak_config_from_vault(
    realm: str = "voyager",
) -> Dict[str, str]:
    """Load Keycloak configuration from Vault.

    Reads from ``voyager/keycloak/<realm>``.

    Args:
        realm: Keycloak realm name.

    Returns:
        Dictionary with url, realm, client_id, client_secret.
    """
    try:
        data = vault_client.get_secret(f"keycloak/{realm}")
        if isinstance(data, dict):
            return {
                "url": data.get("url", ""),
                "realm": data.get("realm", realm),
                "client_id": data.get("client_id", ""),
                "client_secret": data.get("client_secret", ""),
            }
    except Exception as exc:
        logger.warning(
            "Failed to load Keycloak config from Vault for '%s': %s", realm, exc
        )

    # Fallback to environment
    return {
        "url": os.environ.get("KEYCLOAK_URL", os.environ.get("VOYAGER_KEYCLOAK_URL", "")),
        "realm": os.environ.get("KEYCLOAK_REALM", os.environ.get("VOYAGER_KEYCLOAK_REALM", realm)),
        "client_id": os.environ.get("KEYCLOAK_CLIENT_ID", os.environ.get("VOYAGER_KEYCLOAK_CLIENT_ID", "")),
        "client_secret": os.environ.get(
            "KEYCLOAK_CLIENT_SECRET",
            os.environ.get("VOYAGER_KEYCLOAK_CLIENT_SECRET", ""),
        ),
    }


def get_celery_config_from_vault(
    queue: str = "voyager",
) -> Dict[str, str]:
    """Load Celery broker configuration from Vault.

    Reads from ``voyager/celery/<queue>``.

    Args:
        queue: Celery queue name.

    Returns:
        Dictionary with broker_url, result_backend, task_serializer, etc.
    """
    try:
        data = vault_client.get_secret(f"celery/{queue}")
        if isinstance(data, dict):
            return {
                "broker_url": data.get("broker_url", ""),
                "result_backend": data.get("result_backend", ""),
                "task_serializer": data.get("task_serializer", "json"),
                "accept_content": data.get("accept_content", "json"),
                "result_serializer": data.get("result_serializer", "json"),
                "timezone": data.get("timezone", "UTC"),
            }
    except Exception as exc:
        logger.warning(
            "Failed to load Celery config from Vault for '%s': %s", queue, exc
        )

    redis_url = os.environ.get("REDIS_URL", os.environ.get("VOYAGER_REDIS_URL", "redis://redis:6379/0"))
    return {
        "broker_url": redis_url,
        "result_backend": redis_url,
        "task_serializer": "json",
        "accept_content": "json",
        "result_serializer": "json",
        "timezone": "UTC",
    }


def get_minio_config_from_vault(
    bucket: str = "voyager",
) -> Dict[str, str]:
    """Load MinIO/S3 configuration from Vault.

    Reads from ``voyager/minio/<bucket>``.

    Args:
        bucket: S3 bucket/tenant identifier.

    Returns:
        Dictionary with endpoint, access_key, secret_key, bucket, secure.
    """
    try:
        data = vault_client.get_secret(f"minio/{bucket}")
        if isinstance(data, dict):
            return {
                "endpoint": data.get("endpoint", ""),
                "access_key": data.get("access_key", ""),
                "secret_key": data.get("secret_key", ""),
                "bucket": data.get("bucket", bucket),
                "secure": data.get("secure", "false"),
            }
    except Exception as exc:
        logger.warning(
            "Failed to load MinIO config from Vault for '%s': %s", bucket, exc
        )

    return {
        "endpoint": os.environ.get("MINIO_ENDPOINT", os.environ.get("VOYANT_MINIO_ENDPOINT", "")),
        "access_key": os.environ.get("MINIO_ACCESS_KEY", os.environ.get("VOYANT_MINIO_ACCESS_KEY", "")),
        "secret_key": os.environ.get("MINIO_SECRET_KEY", os.environ.get("VOYANT_MINIO_SECRET_KEY", "")),
        "bucket": bucket,
        "secure": "false",
    }


def get_email_config_from_vault(
    provider: str = "smtp",
) -> Dict[str, str]:
    """Load email/SMTP configuration from Vault.

    Reads from ``voyager/email/<provider>``.

    Args:
        provider: Email provider name.

    Returns:
        Dictionary with host, port, username, password, use_tls.
    """
    try:
        data = vault_client.get_secret(f"email/{provider}")
        if isinstance(data, dict):
            return {
                "host": data.get("host", ""),
                "port": str(data.get("port", "587")),
                "username": data.get("username", ""),
                "password": data.get("password", ""),
                "use_tls": str(data.get("use_tls", "true")),
                "from_email": data.get("from_email", ""),
            }
    except Exception as exc:
        logger.warning(
            "Failed to load email config from Vault for '%s': %s", provider, exc
        )

    return {
        "host": os.environ.get("EMAIL_HOST", "localhost"),
        "port": os.environ.get("EMAIL_PORT", "587"),
        "username": os.environ.get("EMAIL_HOST_USER", ""),
        "password": os.environ.get("EMAIL_HOST_PASSWORD", ""),
        "use_tls": "true",
        "from_email": os.environ.get("DEFAULT_FROM_EMAIL", "webmaster@localhost"),
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _load_from_env(prefix: str) -> Dict[str, Any]:
    """Collect environment variables starting with prefix.

    Strips the prefix and lowercases keys for consistent naming.

    Args:
        prefix: Environment variable prefix string.

    Returns:
        Dictionary of env var key-value pairs.
    """
    result: Dict[str, Any] = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            clean_key = key[len(prefix) :].lower()
            result[clean_key] = value
    logger.info("Loaded %d settings from environment with prefix '%s'", len(result), prefix)
    return result


def _build_django_db_config(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Vault database secret to Django DATABASES format.

    Args:
        data: Raw secret data from Vault.

    Returns:
        Django DATABASES dictionary entry.
    """
    return {
        "ENGINE": data.get("engine", "django.db.backends.postgresql"),
        "NAME": data.get("name", "voyager"),
        "USER": data.get("user", ""),
        "PASSWORD": data.get("password", ""),
        "HOST": data.get("host", "postgres"),
        "PORT": data.get("port", "5432"),
        "OPTIONS": data.get("options", {}),
        "CONN_MAX_AGE": data.get("conn_max_age", 600),
        "CONN_HEALTH_CHECKS": data.get("conn_health_checks", True),
    }


def _parse_database_url(url: str) -> Dict[str, Any]:
    """Parse a DATABASE_URL-style connection string.

    Args:
        url: PostgreSQL connection URL.

    Returns:
        Django DATABASES dictionary entry.
    """
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username or "",
            "PASSWORD": parsed.password or "",
            "HOST": parsed.hostname or "localhost",
            "PORT": parsed.port or "5432",
        }
    except Exception:
        logger.warning("Failed to parse DATABASE_URL, using defaults")
        return _default_db_config()


def _default_db_config() -> Dict[str, Any]:
    """Return default database config for local development.

    Returns:
        Dictionary with local development defaults.
    """
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "voyager"),
        "USER": os.environ.get("POSTGRES_USER", "voyager"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "voyager"),
        "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
