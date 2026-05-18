"""Tests for the Assets (DAM) module."""

from __future__ import annotations

from datetime import date, timedelta

from django.test import TestCase

from apps.assets.models import (
    Asset,
    AssetFolder,
)
from apps.assets.services.analytics import AnalyticsService
from apps.assets.services.licensing import LicensingService
from apps.assets.services.organization import OrganizationService
from apps.assets.services.storage import StorageService
from apps.assets.services.versioning import VersioningService


class StorageServiceTests(TestCase):
    """Tests for the StorageService utility functions."""

    def test_detect_file_type_image(self):
        result = StorageService.validate_file("photo.jpg", 1024)
        self.assertTrue(result["valid"])
        self.assertEqual(result["file_type"], "image")

    def test_detect_file_type_video(self):
        result = StorageService.validate_file("clip.mp4", 1024)
        self.assertTrue(result["valid"])
        self.assertEqual(result["file_type"], "video")

    def test_detect_file_type_unknown(self):
        result = StorageService.validate_file("data.xyz", 1024)
        self.assertFalse(result["valid"])
        self.assertEqual(result["file_type"], "unknown")

    def test_validate_file_size_exceeded(self):
        result = StorageService.validate_file("huge.jpg", 200 * 1024 * 1024)
        self.assertFalse(result["valid"])

    def test_generate_file_key(self):
        key = StorageService.generate_file_key("t1", "a1", "file.png")
        self.assertEqual(key, "t1/a1/file.png")

    def test_generate_thumbnail_key(self):
        key = StorageService.generate_thumbnail_key("t1", "a1", 300)
        self.assertEqual(key, "t1/a1/thumbs/300.jpg")


class OrganizationServiceTests(TestCase):
    """Tests for the OrganizationService."""

    def setUp(self):
        self.tenant = "test-tenant"
        self.root = AssetFolder.objects.create(tenant_id=self.tenant, name="Root")

    def test_create_folder(self):
        folder = OrganizationService.create_folder(self.tenant, "Marketing")
        self.assertEqual(folder.name, "Marketing")
        self.assertEqual(folder.tenant_id, self.tenant)

    def test_create_nested_folder(self):
        child = OrganizationService.create_folder(self.tenant, "Child", str(self.root.id))
        self.assertEqual(child.parent, self.root)
        self.assertIn("Root/Child", child.path)

    def test_list_folders(self):
        results = OrganizationService.list_folders(self.tenant)
        self.assertEqual(len(results), 1)

    def test_update_folder(self):
        updated = OrganizationService.update_folder(self.tenant, str(self.root.id), "NewName")
        self.assertIsNotNone(updated)
        self.assertEqual(updated.name, "NewName")

    def test_delete_folder(self):
        folder = OrganizationService.create_folder(self.tenant, "ToDelete")
        success = OrganizationService.delete_folder(self.tenant, str(folder.id))
        self.assertTrue(success)

    def test_folder_tree(self):
        OrganizationService.create_folder(self.tenant, "Child", str(self.root.id))
        tree = OrganizationService.get_folder_tree(self.tenant)
        self.assertTrue(len(tree) >= 1)

    def test_collection_crud(self):
        coll = OrganizationService.create_collection(self.tenant, "My Collection")
        self.assertEqual(coll.name, "My Collection")

        fetched = OrganizationService.get_collection(self.tenant, str(coll.id))
        self.assertEqual(fetched.id, coll.id)

        updated = OrganizationService.update_collection(self.tenant, str(coll.id), "Renamed")
        self.assertEqual(updated.name, "Renamed")

        success = OrganizationService.delete_collection(self.tenant, str(coll.id))
        self.assertTrue(success)


class VersioningServiceTests(TestCase):
    """Tests for the VersioningService."""

    def setUp(self):
        self.tenant = "test-tenant"
        self.asset = Asset.objects.create(
            tenant_id=self.tenant,
            name="Test Asset",
            file_key="k1",
            file_type="image",
            file_size=100,
            uploaded_by="user1",
        )

    def test_create_version(self):
        v = VersioningService.create_version(self.asset, "k2", 200, "Updated colors", "user1")
        self.assertEqual(v.version_number, 2)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.file_key, "k2")
        self.assertEqual(self.asset.version_number, 2)

    def test_list_versions(self):
        VersioningService.create_version(self.asset, "k2", 200, "v2", "user1")
        versions = VersioningService.list_versions(str(self.asset.id))
        self.assertEqual(len(versions), 1)

    def test_rollback(self):
        VersioningService.create_version(self.asset, "k2", 200, "v2", "user1")
        VersioningService.rollback(self.asset, 1)
        self.asset.refresh_from_db()
        self.assertIn("v1", self.asset.file_key)

    def test_delete_version(self):
        v = VersioningService.create_version(self.asset, "k2", 200, "v2", "user1")
        success = VersioningService.delete_version(str(self.asset.id), v.version_number)
        self.assertTrue(success)

    def test_compare_versions(self):
        VersioningService.create_version(self.asset, "k2", 200, "v2", "user1")
        diff = VersioningService.compare_versions(self.asset, 1, 2)
        self.assertIn(diff["type"], ["image_diff", "binary"])


class LicensingServiceTests(TestCase):
    """Tests for the LicensingService."""

    def setUp(self):
        self.tenant = "test-tenant"
        self.asset = Asset.objects.create(
            tenant_id=self.tenant,
            name="Licensed Asset",
            file_key="k1",
            file_type="image",
            uploaded_by="user1",
        )

    def test_create_license(self):
        lic = LicensingService.create_license(self.asset, "rights_managed", "Acme Corp")
        self.assertEqual(lic.license_type, "rights_managed")
        self.assertEqual(lic.holder, "Acme Corp")

    def test_check_compliance(self):
        lic = LicensingService.create_license(
            self.asset,
            "rights_managed",
            valid_until=date.today() + timedelta(days=10),
        )
        result = LicensingService.check_compliance(lic)
        self.assertEqual(result["status"], "compliant")
        self.assertEqual(result["grade"], "A")

    def test_expired_compliance(self):
        lic = LicensingService.create_license(
            self.asset,
            "rights_managed",
            valid_until=date.today() - timedelta(days=5),
        )
        result = LicensingService.check_compliance(lic)
        self.assertEqual(result["status"], "violation")
        self.assertTrue(any(w["type"] == "expired" for w in result["warnings"]))

    def test_find_expiring_licenses(self):
        LicensingService.create_license(
            self.asset,
            valid_until=date.today() + timedelta(days=15),
        )
        results = LicensingService.find_expiring_licenses(self.tenant, 30)
        self.assertEqual(len(results), 1)

    def test_find_expired_licenses(self):
        LicensingService.create_license(
            self.asset,
            valid_until=date.today() - timedelta(days=5),
        )
        results = LicensingService.find_expired_licenses(self.tenant)
        self.assertEqual(len(results), 1)


class AnalyticsServiceTests(TestCase):
    """Tests for the AnalyticsService."""

    def setUp(self):
        self.tenant = "test-tenant"
        self.asset = Asset.objects.create(
            tenant_id=self.tenant,
            name="Analytics Asset",
            file_key="k1",
            file_type="image",
            uploaded_by="user1",
        )

    def test_log_usage(self):
        log = AnalyticsService.log_usage(self.asset, "publishing", "rec1", "embed")
        self.assertEqual(log.used_by_module, "publishing")
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.usage_count, 1)

    def test_get_usage_stats(self):
        AnalyticsService.log_usage(self.asset, "publishing", "rec1", "embed")
        stats = AnalyticsService.get_usage_stats(str(self.asset.id))
        self.assertEqual(stats["total_usage"], 1)

    def test_get_usage_log(self):
        AnalyticsService.log_usage(self.asset, "publishing", "rec1", "embed")
        logs = AnalyticsService.get_usage_log(str(self.asset.id))
        self.assertEqual(len(logs), 1)

    def test_get_tenant_analytics(self):
        AnalyticsService.log_usage(self.asset, "publishing", "rec1", "embed")
        report = AnalyticsService.get_tenant_analytics(self.tenant, 30)
        self.assertEqual(report["total_assets"], 1)
        self.assertEqual(report["used_assets"], 1)

    def test_popular_tags(self):
        self.asset.tags = ["marketing", "hero", "banner"]
        self.asset.save()
        tags = AnalyticsService.get_popular_tags(self.tenant, 10)
        self.assertEqual(len(tags), 3)
