"""Integrations Hub API.

All endpoints are registered in submodules and imported here to assemble
the complete router. The ``router`` is re-exported for registration in
the main API.
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())

# Import all endpoint submodules (self-register on router)
from apps.integrations.api.connections import *  # noqa: E402, F401, F403
from apps.integrations.api.health_ops import *  # noqa: E402, F401, F403
from apps.integrations.api.oauth_endpoints import *  # noqa: E402, F401, F403
from apps.integrations.api.sync_ops import *  # noqa: E402, F401, F403
from apps.integrations.api.webhooks import *  # noqa: E402, F401, F403
