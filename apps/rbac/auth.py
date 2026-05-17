"""Voyager Authentication extending Voyant's KeycloakAuth pattern.

This module re-exports all symbols from ``apps.rbac.auth`` subpackage for
backward compatibility. Use ``from apps.rbac.auth import X`` as before.
"""

# Re-export everything from the auth subpackage for backward compatibility
from apps.rbac.auth import (  # noqa: F401
    VoyagerKeycloakAuth,
    VoyagerKeycloakBearer,
    VoyagerUser,
    get_auth,
    get_current_user,
    get_optional_user,
    require_permission,
    require_role,
    require_workspace_access,
)
