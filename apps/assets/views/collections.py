"""Collection endpoints — CRUD and asset resolution."""

from __future__ import annotations

import uuid

from ninja import Router

from apps.assets.serializers import AssetCollectionIn, AssetCollectionOut, AssetOut
from apps.assets.services.organization import OrganizationService
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


def _get_tenant_id(request) -> str:
    return getattr(request, "tenant_id", "default")


@router.get("/assets/collections", response=list[AssetCollectionOut], tags=["Assets"])
def list_collections(request, search: str | None = None):
    """List asset collections for the tenant."""
    tenant_id = _get_tenant_id(request)
    return OrganizationService.list_collections(tenant_id, search)


@router.post("/assets/collections", response=AssetCollectionOut, tags=["Assets"])
def create_collection(request, payload: AssetCollectionIn):
    """Create a new asset collection."""
    tenant_id = _get_tenant_id(request)
    return OrganizationService.create_collection(
        tenant_id,
        payload.name,
        payload.description,
        [str(a) for a in payload.asset_ids],
        payload.smart_filter,
    )


@router.get("/assets/collections/{collection_id}", response=AssetCollectionOut, tags=["Assets"])
def get_collection(request, collection_id: uuid.UUID):
    """Fetch a single collection."""
    tenant_id = _get_tenant_id(request)
    collection = OrganizationService.get_collection(tenant_id, str(collection_id))
    if not collection:
        from ninja.errors import HttpError

        raise HttpError(404, "Collection not found")
    return collection


@router.put("/assets/collections/{collection_id}", response=AssetCollectionOut, tags=["Assets"])
def update_collection(request, collection_id: uuid.UUID, payload: AssetCollectionIn):
    """Update a collection."""
    tenant_id = _get_tenant_id(request)
    collection = OrganizationService.update_collection(
        tenant_id,
        str(collection_id),
        payload.name,
        payload.description,
        [str(a) for a in payload.asset_ids],
        payload.smart_filter,
    )
    if not collection:
        from ninja.errors import HttpError

        raise HttpError(404, "Collection not found")
    return collection


@router.delete("/assets/collections/{collection_id}", tags=["Assets"])
def delete_collection(request, collection_id: uuid.UUID):
    """Delete a collection."""
    tenant_id = _get_tenant_id(request)
    success = OrganizationService.delete_collection(tenant_id, str(collection_id))
    if not success:
        from ninja.errors import HttpError

        raise HttpError(404, "Collection not found")
    return {"success": True, "id": str(collection_id)}


@router.get("/assets/collections/{collection_id}/assets", response=list[AssetOut], tags=["Assets"])
def collection_assets(request, collection_id: uuid.UUID):
    """Resolve a collection to its assets."""
    tenant_id = _get_tenant_id(request)
    return OrganizationService.get_collection_assets(tenant_id, str(collection_id))
