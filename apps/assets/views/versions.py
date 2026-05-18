"""Version endpoints — listing, creation, rollback, and diff."""

from __future__ import annotations

import uuid

from ninja import Router

from apps.assets.models import Asset
from apps.assets.serializers import (
    AssetRollbackIn,
    AssetVersionDiffOut,
    AssetVersionIn,
    AssetVersionOut,
)
from apps.assets.services.versioning import VersioningService
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


def _get_tenant_id(request) -> str:
    return getattr(request, "tenant_id", "default")


def _get_user_id(request) -> str:
    user = getattr(request, "auth", None)
    if user and hasattr(user, "sub"):
        return str(user.sub)
    return "anonymous"


@router.get("/assets/{asset_id}/versions", response=list[AssetVersionOut], tags=["Assets"])
def list_versions(request, asset_id: uuid.UUID):
    """List all versions of an asset."""
    return VersioningService.list_versions(str(asset_id))


@router.post("/assets/{asset_id}/versions", response=AssetVersionOut, tags=["Assets"])
def create_version(
    request,
    asset_id: uuid.UUID,
    payload: AssetVersionIn,
    new_file_key: str,
    new_file_size: int = 0,
):
    """Create a new version snapshot for an asset."""
    tenant_id = _get_tenant_id(request)
    user_id = _get_user_id(request)
    asset = Asset.objects.get(tenant_id=tenant_id, id=asset_id)
    return VersioningService.create_version(
        asset, new_file_key, new_file_size, payload.change_notes, user_id
    )


@router.get(
    "/assets/{asset_id}/versions/{version_number}/diff",
    response=AssetVersionDiffOut,
    tags=["Assets"],
)
def compare_versions(request, asset_id: uuid.UUID, version_number: int, other: int):
    """Compare two versions of an asset."""
    tenant_id = _get_tenant_id(request)
    asset = Asset.objects.get(tenant_id=tenant_id, id=asset_id)
    return VersioningService.compare_versions(asset, version_number, other)


@router.post("/assets/{asset_id}/rollback", response=AssetVersionOut, tags=["Assets"])
def rollback_version(request, asset_id: uuid.UUID, payload: AssetRollbackIn):
    """Roll back an asset to a previous version."""
    tenant_id = _get_tenant_id(request)
    asset = Asset.objects.get(tenant_id=tenant_id, id=asset_id)
    result = VersioningService.rollback(asset, payload.version_number)
    if not result:
        from ninja.errors import HttpError

        raise HttpError(404, "Target version not found")
    return result
