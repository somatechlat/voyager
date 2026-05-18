"""Tests for assets services — storage, organization, versioning."""

from __future__ import annotations

import uuid

import pytest

from apps.assets.models import Asset, AssetCollection, AssetFolder, AssetVersion
from apps.assets.services import organization as org_service
from apps.assets.services import storage as storage_service
from apps.assets.services import versioning as version_service


@pytest.fixture
def tenant_id() -> str:
    return "test-tenant-assets"


@pytest.fixture
def create_folder(tenant_id, db):
    def _create(**kwargs):
        defaults = {
            "tenant_id": tenant_id,
            "name": f"Folder {uuid.uuid4().hex[:8]}",
        }
        defaults.update(kwargs)
        return AssetFolder.objects.create(**defaults)

    return _create


@pytest.fixture
def create_asset(tenant_id, db):
    def _create(**kwargs):
        defaults = {
            "tenant_id": tenant_id,
            "name": f"Asset {uuid.uuid4().hex[:8]}.jpg",
            "file_key": f"{tenant_id}/{uuid.uuid4()}/image.jpg",
            "file_type": Asset.FileType.IMAGE,
            "file_size": 1024000,
            "mime_type": "image/jpeg",
            "width": 1920,
            "height": 1080,
            "uploaded_by": "user-1",
            "tags": ["tag1", "tag2"],
        }
        defaults.update(kwargs)
        return Asset.objects.create(**defaults)

    return _create


@pytest.fixture
def create_collection(tenant_id, db):
    def _create(**kwargs):
        defaults = {
            "tenant_id": tenant_id,
            "name": f"Collection {uuid.uuid4().hex[:8]}",
        }
        defaults.update(kwargs)
        return AssetCollection.objects.create(**defaults)

    return _create


# ── Storage Service Tests ─────────────────────────────────────────


class TestStorageService:
    def test_create_asset(self, tenant_id, db):
        asset = storage_service.create_asset(
            tenant_id=tenant_id,
            name="hero_image.jpg",
            file_key="assets/hero.jpg",
            file_type=Asset.FileType.IMAGE,
            file_size=2048000,
            mime_type="image/jpeg",
            uploaded_by="user-1",
        )
        assert asset is not None
        assert asset.name == "hero_image.jpg"
        assert Asset.objects.filter(id=asset.id).exists()

    def test_get_asset(self, create_asset):
        a = create_asset(name="find_me.jpg")
        result = storage_service.get_asset(a.id, "test-tenant-assets")
        assert result is not None
        assert result.name == "find_me.jpg"

    def test_get_asset_wrong_tenant(self, create_asset):
        a = create_asset()
        result = storage_service.get_asset(a.id, "wrong-tenant")
        assert result is None

    def test_delete_asset(self, create_asset):
        a = create_asset(name="to_delete.jpg")
        deleted = storage_service.delete_asset(a.id, "test-tenant-assets")
        assert deleted is True
        assert not Asset.objects.filter(id=a.id).exists()

    def test_list_assets(self, create_asset):
        create_asset(name="asset_a.jpg")
        create_asset(name="asset_b.jpg")
        result = storage_service.list_assets("test-tenant-assets")
        assert result["total"] >= 2

    def test_list_assets_type_filter(self, create_asset):
        create_asset(name="photo.jpg", file_type=Asset.FileType.IMAGE)
        create_asset(name="video.mp4", file_type=Asset.FileType.VIDEO)
        result = storage_service.list_assets("test-tenant-assets", file_type=Asset.FileType.IMAGE)
        assert all(a.file_type == Asset.FileType.IMAGE for a in result["results"])

    def test_create_asset_invalid_type(self, tenant_id):
        with pytest.raises(ValueError):
            storage_service.create_asset(
                tenant_id=tenant_id,
                name="bad.xyz",
                file_key="bad.xyz",
                file_type="invalid_type",
                file_size=100,
            )


# ── Organization Service Tests ────────────────────────────────────


class TestOrganizationService:
    def test_create_folder(self, tenant_id, db):
        folder = org_service.create_folder(
            tenant_id=tenant_id,
            name="Marketing",
        )
        assert folder is not None
        assert folder.name == "Marketing"
        assert AssetFolder.objects.filter(id=folder.id).exists()

    def test_create_nested_folder(self, tenant_id, create_folder):
        parent = create_folder(name="Parent")
        child = org_service.create_folder(
            tenant_id=tenant_id,
            name="Child",
            parent_id=parent.id,
        )
        assert child.parent_id == parent.id
        assert child.path == "/Parent/Child"

    def test_get_folder(self, create_folder):
        f = create_folder(name="My Folder")
        result = org_service.get_folder(f.id, "test-tenant-assets")
        assert result is not None
        assert result.name == "My Folder"

    def test_get_folder_wrong_tenant(self, create_folder):
        f = create_folder()
        result = org_service.get_folder(f.id, "wrong-tenant")
        assert result is None

    def test_move_folder(self, tenant_id, create_folder):
        f1 = create_folder(name="Source")
        f2 = create_folder(name="Target")
        moved = org_service.move_folder(f1.id, f2.id, "test-tenant-assets")
        assert moved.parent_id == f2.id

    def test_delete_folder(self, create_folder):
        f = create_folder(name="To Delete")
        deleted = org_service.delete_folder(f.id, "test-tenant-assets")
        assert deleted is True
        assert not AssetFolder.objects.filter(id=f.id).exists()

    def test_create_collection(self, tenant_id, db):
        coll = org_service.create_collection(
            tenant_id=tenant_id,
            name="Hero Images",
            description="All hero banner images",
        )
        assert coll is not None
        assert coll.name == "Hero Images"
        assert AssetCollection.objects.filter(id=coll.id).exists()

    def test_get_collection(self, create_collection):
        c = create_collection(name="My Collection")
        result = org_service.get_collection(c.id, "test-tenant-assets")
        assert result is not None
        assert result.name == "My Collection"

    def test_add_asset_to_collection(self, create_collection, create_asset):
        coll = create_collection()
        asset = create_asset()
        updated = org_service.add_asset_to_collection(coll.id, asset.id, "test-tenant-assets")
        assert str(asset.id) in updated.asset_ids

    def test_remove_asset_from_collection(self, create_collection, create_asset):
        coll = create_collection(asset_ids=[])
        asset = create_asset()
        coll.asset_ids = [str(asset.id)]
        coll.save()
        updated = org_service.remove_asset_from_collection(coll.id, asset.id, "test-tenant-assets")
        assert str(asset.id) not in updated.asset_ids

    def test_create_folder_empty_name(self, tenant_id):
        with pytest.raises(ValueError):
            org_service.create_folder(tenant_id=tenant_id, name="")


# ── Versioning Service Tests ──────────────────────────────────────


class TestVersioningService:
    def test_create_version(self, create_asset):
        a = create_asset(name="versioned.jpg")
        version = version_service.create_version(
            asset_id=a.id,
            file_key="new/path/versioned.jpg",
            file_size=2048000,
            change_notes="Updated colors",
            created_by="user-1",
        )
        assert version is not None
        assert version.change_notes == "Updated colors"
        assert AssetVersion.objects.filter(id=version.id).exists()

    def test_get_versions(self, create_asset):
        a = create_asset()
        version_service.create_version(
            asset_id=a.id, file_key="v1.jpg", file_size=100, created_by="user-1"
        )
        version_service.create_version(
            asset_id=a.id, file_key="v2.jpg", file_size=200, created_by="user-1"
        )
        result = version_service.get_versions(a.id)
        assert result["total"] >= 2

    def test_revert_to_version(self, create_asset):
        a = create_asset(name="revert_me.jpg", version_number=3)
        AssetVersion.objects.create(
            asset=a,
            file_key="old/revert.jpg",
            file_size=1000,
            version_number=1,
            created_by="user-1",
        )
        AssetVersion.objects.create(
            asset=a,
            file_key="current/revert.jpg",
            file_size=2000,
            version_number=2,
            created_by="user-1",
        )
        reverted = version_service.revert_to_version(asset_id=a.id, version_number=1)
        assert reverted is not None
        assert reverted.file_key == "old/revert.jpg"

    def test_revert_nonexistent_version(self, create_asset):
        a = create_asset()
        result = version_service.revert_to_version(asset_id=a.id, version_number=999)
        assert result is None

    def test_delete_version(self, create_asset):
        a = create_asset()
        v = version_service.create_version(
            asset_id=a.id,
            file_key="delete_me.jpg",
            file_size=100,
            created_by="user-1",
        )
        deleted = version_service.delete_version(v.id)
        assert deleted is True
        assert not AssetVersion.objects.filter(id=v.id).exists()

    def test_get_versions_none_exist(self, create_asset):
        a = create_asset()
        result = version_service.get_versions(a.id)
        assert result["total"] == 0
        assert result["versions"] == []
