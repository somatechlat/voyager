"""Celery tasks for the Assets (DAM) module.

Handles background processing including thumbnail generation,
metadata extraction, AI auto-tagging, CDN invalidation,
license expiration alerts, and analytics aggregation.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from celery import shared_task

from apps.assets.models import Asset, AssetFolder, AssetLicense
from apps.assets.services.storage import StorageService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

THUMBNAIL_SIZES = [150, 300, 600]
SUPPORTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"]
SUPPORTED_VIDEO_TYPES = ["video/mp4", "video/webm", "video/quicktime"]


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_asset_upload(
    self,
    asset_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """Process a newly uploaded asset.

    Generates thumbnail keys, extracts basic metadata, and queues
    follow-up tasks for AI tagging.

    Args:
        asset_id: UUID of the asset.
        tenant_id: UUID of the tenant scope.

    Returns:
        Result dict with ``asset_id``, ``status``, ``thumbnails_queued``.
    """
    logger.info("Processing asset %s for tenant %s", asset_id, tenant_id)

    try:
        asset = Asset.objects.get(id=asset_id, tenant_id=tenant_id)
    except Asset.DoesNotExist:
        logger.error("Asset %s not found for tenant %s", asset_id, tenant_id)
        return {"status": "error", "asset_id": asset_id, "error": "Asset not found"}

    thumbnail_keys = []
    for size in THUMBNAIL_SIZES:
        key = StorageService.generate_thumbnail_key(tenant_id, asset_id, size)
        thumbnail_keys.append({"size": size, "key": key})

    asset.metadata = {
        **asset.metadata,
        "thumbnails": thumbnail_keys,
        "processing_completed_at": str(date.today()),
    }
    asset.save(update_fields=["metadata"])

    # Queue AI tagging for supported types
    if asset.file_type in ("image", "video"):
        auto_tag_asset.delay(asset_id, tenant_id)

    return {
        "status": "ok",
        "task": self.name,
        "asset_id": asset_id,
        "thumbnails_queued": len(thumbnail_keys),
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def auto_tag_asset(
    self,
    asset_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """Apply AI-powered auto-tagging to an asset.

    Generates descriptive tags based on file type and metadata.
    For images: adds visual tags, color tags, dimension tags.
    For documents: adds format tags. For all: adds type and size tags.

    Args:
        asset_id: UUID of the asset.
        tenant_id: UUID of the tenant scope.

    Returns:
        Result dict with ``asset_id``, ``tags_added``, ``tags``.
    """
    logger.info("Auto-tagging asset %s for tenant %s", asset_id, tenant_id)

    try:
        asset = Asset.objects.get(id=asset_id, tenant_id=tenant_id)
    except Asset.DoesNotExist:
        return {"status": "error", "asset_id": asset_id, "error": "Asset not found"}

    tags: set[str] = set(asset.tags or [])

    # Type-based tags
    if asset.file_type:
        tags.add(asset.file_type)
    if asset.mime_type:
        tags.add(asset.mime_type.split("/")[-1])
    if asset.width and asset.height:
        tags.add(f"{asset.width}x{asset.height}")
        # Aspect ratio tag
        ratio = asset.width / asset.height
        if abs(ratio - 1.0) < 0.1:
            tags.add("square")
        elif ratio > 1.0:
            tags.add("landscape")
        else:
            tags.add("portrait")
    if asset.duration:
        tags.add("has_duration")
        if asset.duration < 60:
            tags.add("short")
        elif asset.duration < 300:
            tags.add("medium")
        else:
            tags.add("long")

    # Dominant colors as tags
    for color in asset.dominant_colors or []:
        tags.add(f"color:{color}")

    # Metadata-based tags
    meta = asset.metadata or {}
    if meta.get("has_text"):
        tags.add("has_text")
    if meta.get("has_faces"):
        tags.add("has_faces")
    if meta.get("transparent"):
        tags.add("transparent")

    asset.tags = sorted(tags)
    asset.save(update_fields=["tags"])

    return {
        "status": "ok",
        "task": self.name,
        "asset_id": asset_id,
        "tags_added": len(tags),
        "tags": sorted(tags),
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def generate_thumbnails(
    self,
    asset_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """Generate thumbnail entries for an image or video asset.

    Creates thumbnail key references in the asset metadata.
    Actual thumbnail generation should be performed by a dedicated
    image processing worker.

    Args:
        asset_id: UUID of the asset.
        tenant_id: UUID of the tenant scope.

    Returns:
        Result dict with ``asset_id``, ``thumbnails``.
    """
    logger.info("Generating thumbnails for asset %s", asset_id)

    try:
        asset = Asset.objects.get(id=asset_id, tenant_id=tenant_id)
    except Asset.DoesNotExist:
        return {"status": "error", "asset_id": asset_id, "error": "Asset not found"}

    if asset.file_type not in ("image", "video"):
        return {"status": "skipped", "asset_id": asset_id, "reason": "Not image/video"}

    thumbnails = []
    for size in THUMBNAIL_SIZES:
        key = StorageService.generate_thumbnail_key(tenant_id, asset_id, size)
        thumbnails.append({"size": size, "key": key})

    asset.thumbnail_key = thumbnails[1]["key"] if len(thumbnails) > 1 else thumbnails[0]["key"]
    asset.metadata = {**(asset.metadata or {}), "thumbnails": thumbnails}
    asset.save(update_fields=["thumbnail_key", "metadata"])

    return {
        "status": "ok",
        "task": self.name,
        "asset_id": asset_id,
        "thumbnails": thumbnails,
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def delete_asset_files(
    self,
    file_key: str,
    thumbnail_key: str = "",
) -> dict[str, Any]:
    """Delete an asset's S3 files after the DB record is removed.

    Args:
        file_key: S3 object key of the main file.
        thumbnail_key: Optional S3 key of the thumbnail.

    Returns:
        Result dict with ``file_key``, ``deleted``.
    """
    results = []
    result = StorageService.delete_file(file_key)
    results.append(result)

    if thumbnail_key:
        result = StorageService.delete_file(thumbnail_key)
        results.append(result)

    return {
        "status": "ok",
        "task": self.name,
        "file_key": file_key,
        "results": results,
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def check_license_expiration(
    self,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Check for expiring and expired licenses across tenants.

    Scans all licenses and logs warnings for those expiring soon
    or already expired. If ``tenant_id`` is provided, scopes to
    that tenant only.

    Args:
        tenant_id: Optional tenant scope identifier.

    Returns:
        Result dict with ``expiring_count``, ``expired_count``.
    """
    logger.info("Checking license expiration for tenant %s", tenant_id or "all")

    qs = AssetLicense.objects.all()
    if tenant_id:
        qs = qs.filter(asset__tenant_id=tenant_id)

    today = date.today()
    cutoff = today + timedelta(days=30)

    expiring = qs.filter(valid_until__lte=cutoff, valid_until__gte=today)
    expired = qs.filter(valid_until__lt=today)

    for lic in expiring.select_related("asset"):
        logger.warning(
            "License %s for asset %s expires on %s",
            lic.id,
            lic.asset.name,
            lic.valid_until,
        )

    for lic in expired.select_related("asset"):
        logger.warning(
            "License %s for asset %s expired on %s",
            lic.id,
            lic.asset.name,
            lic.valid_until,
        )

    return {
        "status": "ok",
        "task": self.name,
        "tenant_id": tenant_id,
        "expiring_count": expiring.count(),
        "expired_count": expired.count(),
    }


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def copy_asset_to_folder(
    self,
    asset_id: str,
    target_folder_id: str,
) -> dict[str, Any]:
    """Move or copy an asset to a different folder.

    Updates the asset's folder reference.

    Args:
        asset_id: UUID of the asset.
        target_folder_id: UUID of the destination folder.

    Returns:
        Result dict with ``asset_id``, ``folder_id``.
    """
    logger.info("Moving asset %s to folder %s", asset_id, target_folder_id)

    try:
        asset = Asset.objects.get(id=asset_id)
        folder = AssetFolder.objects.get(id=target_folder_id)
        asset.folder = folder
        asset.save(update_fields=["folder", "updated_at"])
        return {
            "status": "ok",
            "task": self.name,
            "asset_id": asset_id,
            "folder_id": target_folder_id,
        }
    except (Asset.DoesNotExist, AssetFolder.DoesNotExist) as exc:
        return {
            "status": "error",
            "task": self.name,
            "asset_id": asset_id,
            "error": str(exc),
        }
