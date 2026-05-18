"""Asset endpoints — CRUD, upload, and download."""

from __future__ import annotations

import logging
import uuid

from django.db.models import Q
from ninja import File, Query, Router
from ninja.files import UploadedFile

from apps.assets.models import Asset, AssetFolder
from apps.assets.serializers import (
    AssetBulkUploadItem,
    AssetBulkUploadResponse,
    AssetIn,
    AssetOut,
    AssetSearchFilters,
    AssetUpdateIn,
    AssetUploadResponse,
)
from apps.assets.services.storage import StorageService
from apps.rbac.auth import VoyagerKeycloakBearer

logger = logging.getLogger(__name__)

router = Router(auth=VoyagerKeycloakBearer())


def _get_tenant_id(request) -> str:
    return getattr(request, "tenant_id", "default")


def _get_user_id(request) -> str:
    user = getattr(request, "auth", None)
    if user and hasattr(user, "sub"):
        return str(user.sub)
    return "anonymous"


@router.get("/assets", response=list[AssetOut], tags=["Assets"])
def list_assets(
    request,
    filters: Query[AssetSearchFilters],
    limit: int = 20,
    offset: int = 0,
):
    """List assets for the tenant with optional filters."""
    tenant_id = _get_tenant_id(request)
    qs = Asset.objects.filter(tenant_id=tenant_id)
    if filters.file_type:
        qs = qs.filter(file_type=filters.file_type)
    if filters.folder_id:
        qs = qs.filter(folder_id=filters.folder_id)
    if filters.uploaded_by:
        qs = qs.filter(uploaded_by=filters.uploaded_by)
    if filters.tags:
        for tag in filters.tags:
            qs = qs.filter(tags__contains=[tag])
    if filters.date_from:
        qs = qs.filter(created_at__gte=filters.date_from)
    if filters.date_to:
        qs = qs.filter(created_at__lte=filters.date_to)
    if filters.search:
        qs = qs.filter(
            Q(name__icontains=filters.search)
            | Q(description__icontains=filters.search)
            | Q(tags__icontains=filters.search)
        )
    return list(qs.order_by("-created_at")[offset : offset + limit])


@router.post("/assets", response=AssetOut, tags=["Assets"])
def create_asset(request, payload: AssetIn):
    """Create an asset record after a file has been uploaded to S3."""
    tenant_id = _get_tenant_id(request)
    user_id = _get_user_id(request)
    folder = None
    if payload.folder_id:
        try:
            folder = AssetFolder.objects.get(tenant_id=tenant_id, id=payload.folder_id)
        except AssetFolder.DoesNotExist:
            folder = None
    asset = Asset.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        folder=folder,
        file_key="",
        file_type=payload.file_type,
        file_size=payload.file_size,
        mime_type=payload.mime_type,
        width=payload.width,
        height=payload.height,
        duration=payload.duration,
        tags=payload.tags or [],
        metadata=payload.metadata or {},
        dominant_colors=payload.dominant_colors or [],
        uploaded_by=user_id,
    )
    return asset


@router.get("/assets/{asset_id}", response=AssetOut, tags=["Assets"])
def get_asset(request, asset_id: uuid.UUID):
    """Fetch a single asset by ID."""
    tenant_id = _get_tenant_id(request)
    return Asset.objects.get(tenant_id=tenant_id, id=asset_id)


@router.put("/assets/{asset_id}", response=AssetOut, tags=["Assets"])
def update_asset(request, asset_id: uuid.UUID, payload: AssetUpdateIn):
    """Update an asset's metadata."""
    tenant_id = _get_tenant_id(request)
    asset = Asset.objects.get(tenant_id=tenant_id, id=asset_id)
    if payload.name is not None:
        asset.name = payload.name
    if payload.description is not None:
        asset.description = payload.description
    if payload.folder_id is not None:
        if payload.folder_id:
            asset.folder = AssetFolder.objects.get(tenant_id=tenant_id, id=payload.folder_id)
        else:
            asset.folder = None
    if payload.tags is not None:
        asset.tags = payload.tags
    if payload.metadata is not None:
        asset.metadata = payload.metadata
    asset.save()
    return asset


@router.delete("/assets/{asset_id}", tags=["Assets"])
def delete_asset(request, asset_id: uuid.UUID):
    """Delete an asset and its S3 file."""
    tenant_id = _get_tenant_id(request)
    asset = Asset.objects.get(tenant_id=tenant_id, id=asset_id)
    if asset.file_key:
        StorageService.delete_file(asset.file_key)
    if asset.thumbnail_key:
        StorageService.delete_file(asset.thumbnail_key)
    asset.delete()
    return {"success": True, "id": str(asset_id)}


@router.post("/assets/upload", response=AssetUploadResponse, tags=["Assets"])
def upload_asset(
    request,
    name: str,
    folder_id: uuid.UUID | None = None,
    description: str = "",
    file: UploadedFile = File(...),
):
    """Upload a file to S3/MinIO and create an asset record."""
    tenant_id = _get_tenant_id(request)
    user_id = _get_user_id(request)
    filename = file.name or "unnamed"
    file_size = file.size or 0
    validation = StorageService.validate_file(filename, file_size)
    if not validation["valid"]:
        from ninja.errors import HttpError

        raise HttpError(400, validation.get("error", "File validation failed"))
    asset_id = uuid.uuid4()
    file_key = StorageService.generate_file_key(tenant_id, str(asset_id), filename)
    result = StorageService.upload_file(
        file_data=file.read(),
        file_key=file_key,
        content_type=validation["mime_type"],
    )
    if not result["success"]:
        from ninja.errors import HttpError

        raise HttpError(500, result.get("error", "Upload failed"))
    folder = None
    if folder_id:
        try:
            folder = AssetFolder.objects.get(tenant_id=tenant_id, id=folder_id)
        except AssetFolder.DoesNotExist:
            folder = None
    asset = Asset.objects.create(
        id=asset_id,
        tenant_id=tenant_id,
        name=name or filename,
        description=description,
        folder=folder,
        file_key=file_key,
        file_type=validation["file_type"],
        file_size=file_size,
        mime_type=validation["mime_type"],
        uploaded_by=user_id,
    )
    presigned = StorageService.generate_presigned_url(file_key)
    return {
        "id": asset.id,
        "name": asset.name,
        "file_key": asset.file_key,
        "file_type": asset.file_type,
        "file_size": asset.file_size,
        "mime_type": asset.mime_type,
        "thumbnail_key": "",
        "presigned_url": presigned,
    }


@router.post("/assets/upload-bulk", response=AssetBulkUploadResponse, tags=["Assets"])
def upload_bulk(request, items: list[AssetBulkUploadItem]):
    """Generate presigned POST URLs for bulk file uploads."""
    tenant_id = _get_tenant_id(request)
    presigned_posts: list[dict] = []
    asset_ids: list[uuid.UUID] = []
    for item in items:
        validation = StorageService.validate_file(item.filename, item.file_size)
        if not validation["valid"]:
            continue
        asset_id = uuid.uuid4()
        file_key = StorageService.generate_file_key(tenant_id, str(asset_id), item.filename)
        post = StorageService.generate_presigned_post(
            file_key=file_key,
            content_type=item.content_type or validation["mime_type"],
            expiration=3600,
            max_size=validation["max_size"],
        )
        if post:
            presigned_posts.append(
                {
                    "asset_id": asset_id,
                    "filename": item.filename,
                    "url": post["url"],
                    "fields": post["fields"],
                    "file_key": file_key,
                    "file_type": validation["file_type"],
                }
            )
            asset_ids.append(asset_id)
    return {"presigned_posts": presigned_posts, "asset_ids": asset_ids}


@router.get("/assets/{asset_id}/download", tags=["Assets"])
def download_asset(request, asset_id: uuid.UUID):
    """Generate a presigned download URL for an asset."""
    tenant_id = _get_tenant_id(request)
    asset = Asset.objects.get(tenant_id=tenant_id, id=asset_id)
    url = StorageService.generate_presigned_url(asset.file_key)
    if not url:
        from ninja.errors import HttpError

        raise HttpError(500, "Failed to generate download URL")
    return {"download_url": url, "filename": asset.name, "expires_in": 3600}
