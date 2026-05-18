"""Folder endpoints — CRUD and tree hierarchy."""

from __future__ import annotations

import uuid

from ninja import Router

from apps.assets.serializers import AssetFolderIn, AssetFolderOut, AssetFolderTreeOut
from apps.assets.services.organization import OrganizationService
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


def _get_tenant_id(request) -> str:
    return getattr(request, "tenant_id", "default")


@router.get("/assets/folders", response=list[AssetFolderOut], tags=["Assets"])
def list_folders(
    request,
    parent_id: uuid.UUID | None = None,
    search: str | None = None,
):
    """List folders for the tenant."""
    tenant_id = _get_tenant_id(request)
    return OrganizationService.list_folders(tenant_id, parent_id, search)


@router.post("/assets/folders", response=AssetFolderOut, tags=["Assets"])
def create_folder(request, payload: AssetFolderIn):
    """Create a new folder."""
    tenant_id = _get_tenant_id(request)
    return OrganizationService.create_folder(tenant_id, payload.name, payload.parent_id)


@router.get("/assets/folders/{folder_id}", response=AssetFolderOut, tags=["Assets"])
def get_folder(request, folder_id: uuid.UUID):
    """Fetch a single folder."""
    tenant_id = _get_tenant_id(request)
    folder = OrganizationService.get_folder(tenant_id, str(folder_id))
    if not folder:
        from ninja.errors import HttpError

        raise HttpError(404, "Folder not found")
    return folder


@router.put("/assets/folders/{folder_id}", response=AssetFolderOut, tags=["Assets"])
def update_folder(request, folder_id: uuid.UUID, payload: AssetFolderIn):
    """Update a folder's name or parent."""
    tenant_id = _get_tenant_id(request)
    folder = OrganizationService.update_folder(
        tenant_id, str(folder_id), payload.name, payload.parent_id
    )
    if not folder:
        from ninja.errors import HttpError

        raise HttpError(404, "Folder not found")
    return folder


@router.delete("/assets/folders/{folder_id}", tags=["Assets"])
def delete_folder(request, folder_id: uuid.UUID):
    """Delete a folder."""
    tenant_id = _get_tenant_id(request)
    success = OrganizationService.delete_folder(tenant_id, str(folder_id))
    if not success:
        from ninja.errors import HttpError

        raise HttpError(400, "Folder not found or has children")
    return {"success": True, "id": str(folder_id)}


@router.get("/assets/folders/tree", response=list[AssetFolderTreeOut], tags=["Assets"])
def folder_tree(request):
    """Return the full folder hierarchy as a tree."""
    tenant_id = _get_tenant_id(request)
    return OrganizationService.get_folder_tree(tenant_id)
