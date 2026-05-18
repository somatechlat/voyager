"""Assets (DAM) API — Main router.

Aggregates sub-routers from views/ for assets, folders, collections,
versions, licenses, and usage analytics. All endpoints require
Keycloak JWT authentication.
"""

from __future__ import annotations

from ninja import Router

from apps.assets.views.assets import router as assets_router
from apps.assets.views.collections import router as collections_router
from apps.assets.views.folders import router as folders_router
from apps.assets.views.licenses import router as licenses_router
from apps.assets.views.usage import router as usage_router
from apps.assets.views.versions import router as versions_router
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())

# Register all sub-routers
router.add_router("", assets_router)
router.add_router("", folders_router)
router.add_router("", collections_router)
router.add_router("", versions_router)
router.add_router("", licenses_router)
router.add_router("", usage_router)
