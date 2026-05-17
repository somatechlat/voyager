"""Voyager Authentication extending Voyant's KeycloakAuth pattern.

This module implements JWT authentication and role-based authorization for the
Voyager marketing automation platform. It extends Voyant's ``KeycloakAuth`` and
``KeycloakBearer`` classes with Voyager-specific roles, workspace-scoped access
control, and granular marketing permissions.

Patterns inherited from Voyant:
- JWKS caching with httpx
- RS256 token validation via python-jose
- ``get_auth()`` singleton factory
- ``HttpBearer`` integration with Django Ninja
- ``require_role`` / ``require_permission`` dependency factories
"""

from .bearer import VoyagerKeycloakBearer
from .dependencies import (
    get_auth,
    get_current_user,
    get_optional_user,
    require_permission,
    require_role,
    require_workspace_access,
)
from .keycloak import VoyagerKeycloakAuth
from .user import VoyagerUser

__all__ = [
    "VoyagerUser",
    "VoyagerKeycloakAuth",
    "VoyagerKeycloakBearer",
    "get_auth",
    "get_current_user",
    "get_optional_user",
    "require_role",
    "require_permission",
    "require_workspace_access",
]
