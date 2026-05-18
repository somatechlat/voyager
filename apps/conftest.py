"""Shared pytest fixtures for all app tests."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest
from django.utils import timezone

from apps.rbac.auth.bearer import VoyagerKeycloakBearer
from apps.rbac.auth.user import VoyagerUser

# ---------------------------------------------------------------------------
# Auth bypass fixture — patches Keycloak auth for all API tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def patch_keycloak_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Automatically patch Keycloak auth so tests can call authenticated endpoints.

    Every request with an ``Authorization: Bearer <anything>`` header will be
    treated as a test user with the ``voyager:read:*`` permission.
    """
    test_user = VoyagerUser(
        user_id="test-user-001",
        email="test@voyager.local",
        username="testuser",
        tenant_id="test-tenant-001",
        roles=["voyager-admin"],
        permissions=["voyager:read:*", "voyager:write:*", "voyager:audit:*"],
    )

    def mock_authenticate(
        self: VoyagerKeycloakBearer,
        request: Any,
        token: str,
    ) -> VoyagerUser | None:
        request.auth = test_user
        return test_user

    monkeypatch.setattr(
        VoyagerKeycloakBearer,
        "authenticate",
        mock_authenticate,
    )


@pytest.fixture
def tenant_id() -> str:
    """Return a consistent tenant ID for test data creation."""
    return "test-tenant-001"


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Return headers that satisfy the patched Keycloak auth."""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def now() -> datetime:
    """Return the current time in UTC."""
    return timezone.now()
