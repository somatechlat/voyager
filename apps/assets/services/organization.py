"""Organization service for folder and collection management.

Handles folder CRUD with hierarchical paths, asset collection management,
and smart collections with dynamic filtering.
"""

from __future__ import annotations

import logging
from typing import Any

from django.db.models import Q

from apps.assets.models import Asset, AssetCollection, AssetFolder

logger = logging.getLogger(__name__)


class OrganizationService:
    """Service for folder and collection organization of assets."""

    # ------------------------------------------------------------------
    # Folders
    # ------------------------------------------------------------------

    @staticmethod
    def list_folders(
        tenant_id: str,
        parent_id: str | None = None,
        search: str | None = None,
    ) -> list[AssetFolder]:
        """List folders scoped to a tenant, optionally filtered.

        Args:
            tenant_id: Tenant scope identifier.
            parent_id: Filter by parent folder UUID (None for root).
            search: Optional case-insensitive name search.

        Returns:
            QuerySet of matching folders.
        """
        qs = AssetFolder.objects.filter(tenant_id=tenant_id)
        if parent_id:
            qs = qs.filter(parent_id=parent_id)
        else:
            qs = qs.filter(parent__isnull=True)
        if search:
            qs = qs.filter(name__icontains=search)
        return list(qs.order_by("name"))

    @staticmethod
    def get_folder(tenant_id: str, folder_id: str) -> AssetFolder | None:
        """Fetch a single folder by ID within a tenant.

        Args:
            tenant_id: Tenant scope identifier.
            folder_id: UUID of the folder.

        Returns:
            The folder instance or ``None`` if not found.
        """
        try:
            return AssetFolder.objects.get(tenant_id=tenant_id, id=folder_id)
        except AssetFolder.DoesNotExist:
            return None

    @staticmethod
    def create_folder(
        tenant_id: str,
        name: str,
        parent_id: str | None = None,
    ) -> AssetFolder:
        """Create a new folder within a tenant.

        Args:
            tenant_id: Tenant scope identifier.
            name: Folder display name.
            parent_id: Optional parent folder UUID.

        Returns:
            The newly created folder.
        """
        parent = None
        if parent_id:
            parent = OrganizationService.get_folder(tenant_id, parent_id)
        folder = AssetFolder.objects.create(
            tenant_id=tenant_id,
            name=name,
            parent=parent,
        )
        return folder

    @staticmethod
    def update_folder(
        tenant_id: str,
        folder_id: str,
        name: str | None = None,
        parent_id: str | None = None,
    ) -> AssetFolder | None:
        """Update a folder's name or parent.

        Args:
            tenant_id: Tenant scope identifier.
            folder_id: UUID of the folder to update.
            name: New folder name.
            parent_id: New parent folder UUID (None for root).

        Returns:
            The updated folder or ``None`` if not found.
        """
        folder = OrganizationService.get_folder(tenant_id, folder_id)
        if not folder:
            return None
        if name is not None:
            folder.name = name
        if parent_id is not None:
            folder.parent = OrganizationService.get_folder(tenant_id, parent_id)
        folder.save()
        return folder

    @staticmethod
    def delete_folder(tenant_id: str, folder_id: str) -> bool:
        """Delete a folder and optionally move assets to parent.

        Folders with child folders cannot be deleted until children
        are removed or reassigned.

        Args:
            tenant_id: Tenant scope identifier.
            folder_id: UUID of the folder to delete.

        Returns:
            ``True`` if deleted, ``False`` if not found or has children.
        """
        folder = OrganizationService.get_folder(tenant_id, folder_id)
        if not folder:
            return False
        if folder.children.exists():
            return False
        Asset.objects.filter(folder=folder).update(folder=folder.parent)
        folder.delete()
        return True

    @staticmethod
    def get_folder_tree(tenant_id: str) -> list[dict[str, Any]]:
        """Return the full folder hierarchy for a tenant.

        Args:
            tenant_id: Tenant scope identifier.

        Returns:
            List of folder dicts with ``id``, ``name``, ``path``,
            ``parent_id``, and nested ``children``.
        """
        folders = AssetFolder.objects.filter(tenant_id=tenant_id).order_by("path")
        folder_map: dict[str, dict[str, Any]] = {}
        for f in folders:
            folder_map[str(f.id)] = {
                "id": str(f.id),
                "name": f.name,
                "path": f.path,
                "parent_id": str(f.parent_id) if f.parent_id else None,
                "children": [],
            }
        roots: list[dict[str, Any]] = []
        for f in folders:
            node = folder_map[str(f.id)]
            if f.parent_id and str(f.parent_id) in folder_map:
                folder_map[str(f.parent_id)]["children"].append(node)
            else:
                roots.append(node)
        return roots

    # ------------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------------

    @staticmethod
    def list_collections(
        tenant_id: str,
        search: str | None = None,
    ) -> list[AssetCollection]:
        """List asset collections for a tenant.

        Args:
            tenant_id: Tenant scope identifier.
            search: Optional name search.

        Returns:
            List of matching collections.
        """
        qs = AssetCollection.objects.filter(tenant_id=tenant_id)
        if search:
            qs = qs.filter(name__icontains=search)
        return list(qs)

    @staticmethod
    def get_collection(tenant_id: str, collection_id: str) -> AssetCollection | None:
        """Fetch a single collection by ID.

        Args:
            tenant_id: Tenant scope identifier.
            collection_id: UUID of the collection.

        Returns:
            The collection instance or ``None``.
        """
        try:
            return AssetCollection.objects.get(tenant_id=tenant_id, id=collection_id)
        except AssetCollection.DoesNotExist:
            return None

    @staticmethod
    def create_collection(
        tenant_id: str,
        name: str,
        description: str = "",
        asset_ids: list[str] | None = None,
        smart_filter: dict[str, Any] | None = None,
    ) -> AssetCollection:
        """Create a new asset collection.

        Args:
            tenant_id: Tenant scope identifier.
            name: Collection name.
            description: Optional description.
            asset_ids: Ordered list of asset UUIDs (static collection).
            smart_filter: Filter dict for smart collection.

        Returns:
            The newly created collection.
        """
        collection = AssetCollection.objects.create(
            tenant_id=tenant_id,
            name=name,
            description=description,
            asset_ids=asset_ids or [],
            smart_filter=smart_filter or {},
        )
        return collection

    @staticmethod
    def update_collection(
        tenant_id: str,
        collection_id: str,
        name: str | None = None,
        description: str | None = None,
        asset_ids: list[str] | None = None,
        smart_filter: dict[str, Any] | None = None,
    ) -> AssetCollection | None:
        """Update a collection's fields.

        Args:
            tenant_id: Tenant scope identifier.
            collection_id: UUID of the collection.
            name: New name.
            description: New description.
            asset_ids: New ordered asset list.
            smart_filter: New smart filter.

        Returns:
            The updated collection or ``None``.
        """
        collection = OrganizationService.get_collection(tenant_id, collection_id)
        if not collection:
            return None
        if name is not None:
            collection.name = name
        if description is not None:
            collection.description = description
        if asset_ids is not None:
            collection.asset_ids = asset_ids
        if smart_filter is not None:
            collection.smart_filter = smart_filter
        collection.save()
        return collection

    @staticmethod
    def delete_collection(tenant_id: str, collection_id: str) -> bool:
        """Delete a collection.

        Args:
            tenant_id: Tenant scope identifier.
            collection_id: UUID of the collection.

        Returns:
            ``True`` if deleted, ``False`` if not found.
        """
        collection = OrganizationService.get_collection(tenant_id, collection_id)
        if not collection:
            return False
        collection.delete()
        return True

    @staticmethod
    def get_collection_assets(
        tenant_id: str,
        collection_id: str,
    ) -> list[Asset]:
        """Resolve a collection to its assets.

        For static collections, returns assets matching stored IDs.
        For smart collections, evaluates the filter against the tenant's assets.

        Args:
            tenant_id: Tenant scope identifier.
            collection_id: UUID of the collection.

        Returns:
            List of matching assets.
        """
        collection = OrganizationService.get_collection(tenant_id, collection_id)
        if not collection:
            return []

        # Static collection: explicit asset IDs
        if collection.asset_ids:
            return list(
                Asset.objects.filter(
                    tenant_id=tenant_id,
                    id__in=collection.asset_ids,
                )
            )

        # Smart collection: evaluate filter
        flt = collection.smart_filter
        if not flt:
            return []

        qs = Asset.objects.filter(tenant_id=tenant_id)
        file_types = flt.get("file_types")
        if file_types:
            qs = qs.filter(file_type__in=file_types)
        tags = flt.get("tags")
        if tags:
            for tag in tags:
                qs = qs.filter(tags__contains=[tag])
        folder_id = flt.get("folder_id")
        if folder_id:
            qs = qs.filter(folder_id=folder_id)
        uploaded_by = flt.get("uploaded_by")
        if uploaded_by:
            qs = qs.filter(uploaded_by=uploaded_by)
        date_from = flt.get("date_from")
        date_to = flt.get("date_to")
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)
        search = flt.get("search")
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(tags__icontains=search)
            )
        return list(qs)
