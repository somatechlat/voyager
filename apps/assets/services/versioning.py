"""Versioning service for asset version control.

Handles version creation, listing, rollback, and diff generation
for tracked asset files.
"""

from __future__ import annotations

import logging
from typing import Any

from apps.assets.models import Asset, AssetVersion
from apps.assets.services.storage import StorageService

logger = logging.getLogger(__name__)


class VersioningService:
    """Service for asset version control operations."""

    @staticmethod
    def list_versions(asset_id: str) -> list[AssetVersion]:
        """List all versions of an asset, newest first.

        Args:
            asset_id: UUID of the parent asset.

        Returns:
            List of version records.
        """
        return list(AssetVersion.objects.filter(asset_id=asset_id))

    @staticmethod
    def get_version(asset_id: str, version_number: int) -> AssetVersion | None:
        """Fetch a specific version by asset and version number.

        Args:
            asset_id: UUID of the parent asset.
            version_number: Sequential version number.

        Returns:
            The version record or ``None``.
        """
        try:
            return AssetVersion.objects.get(
                asset_id=asset_id,
                version_number=version_number,
            )
        except AssetVersion.DoesNotExist:
            return None

    @staticmethod
    def create_version(
        asset: Asset,
        new_file_key: str,
        new_file_size: int,
        change_notes: str,
        created_by: str,
    ) -> AssetVersion:
        """Create a new version snapshot before updating an asset.

        Snapshots the current asset file_key and file_size into a new
        AssetVersion row, then increments the asset's version_number.

        Args:
            asset: The asset being updated.
            new_file_key: S3 key for the new file.
            new_file_size: Size of the new file in bytes.
            change_notes: Description of what changed.
            created_by: UUID of the user creating the version.

        Returns:
            The newly created version record.
        """
        new_version_number = asset.version_number + 1
        version = AssetVersion.objects.create(
            asset=asset,
            file_key=asset.file_key,
            file_size=asset.file_size,
            version_number=new_version_number,
            change_notes=change_notes,
            created_by=created_by,
        )
        asset.file_key = new_file_key
        asset.file_size = new_file_size
        asset.version_number = new_version_number
        asset.save(update_fields=["file_key", "file_size", "version_number", "updated_at"])
        logger.info(
            "Created version %s for asset %s",
            new_version_number,
            asset.id,
        )
        return version

    @staticmethod
    def rollback(asset: Asset, version_number: int) -> AssetVersion | None:
        """Restore an asset to a previous version.

        Creates a new version entry for the current state, then swaps
        the asset's file_key and file_size back to the target version.

        Args:
            asset: The asset to roll back.
            version_number: Target version number to restore.

        Returns:
            The newly created snapshot version, or ``None`` if target
            version does not exist.
        """
        target = VersioningService.get_version(str(asset.id), version_number)
        if not target:
            return None

        current_version = asset.version_number

        # Snapshot current state as a new version
        snapshot = AssetVersion.objects.create(
            asset=asset,
            file_key=asset.file_key,
            file_size=asset.file_size,
            version_number=current_version + 1,
            change_notes=f"Rollback to version {version_number}",
            created_by=asset.uploaded_by,
        )

        # Restore target version's file reference
        asset.file_key = target.file_key
        asset.file_size = target.file_size
        asset.version_number = current_version + 2
        asset.save(update_fields=["file_key", "file_size", "version_number", "updated_at"])

        logger.info(
            "Rolled back asset %s to version %s (now v%s)",
            asset.id,
            version_number,
            asset.version_number,
        )
        return snapshot

    @staticmethod
    def delete_version(asset_id: str, version_number: int) -> bool:
        """Delete a version record and its S3 file.

        Prevents deletion of version 1 (the original upload).

        Args:
            asset_id: UUID of the parent asset.
            version_number: Version number to delete.

        Returns:
            ``True`` if deleted, ``False`` if not found or is version 1.
        """
        if version_number <= 1:
            return False
        version = VersioningService.get_version(asset_id, version_number)
        if not version:
            return False
        StorageService.delete_file(version.file_key)
        version.delete()
        logger.info("Deleted version %s of asset %s", version_number, asset_id)
        return True

    @staticmethod
    def compare_versions(
        asset: Asset,
        version_a: int,
        version_b: int,
    ) -> dict[str, Any]:
        """Generate a comparison between two asset versions.

        For images: returns metadata comparison.
        For documents: returns metadata comparison.
        For other types: returns binary comparison.

        Args:
            asset: The parent asset.
            version_a: First version number.
            version_b: Second version number.

        Returns:
            Comparison dict with type, fields compared, and changes.
        """
        va = VersioningService.get_version(str(asset.id), version_a)
        vb = VersioningService.get_version(str(asset.id), version_b)
        if not va or not vb:
            return {"type": "error", "message": "One or both versions not found"}

        changes: list[dict[str, Any]] = []
        if va.file_size != vb.file_size:
            changes.append(
                {
                    "field": "file_size",
                    "old": va.file_size,
                    "new": vb.file_size,
                    "delta": vb.file_size - va.file_size,
                }
            )

        meta_a = asset.metadata or {}
        changes.append(
            {
                "field": "version",
                "old": va.version_number,
                "new": vb.version_number,
            }
        )

        if asset.file_type == "image":
            return {
                "type": "image_diff",
                "changes": changes,
                "metadata": meta_a,
            }
        if asset.file_type == "document":
            return {
                "type": "text_diff",
                "changes": changes,
                "metadata": meta_a,
            }
        return {"type": "binary", "changes": changes}
