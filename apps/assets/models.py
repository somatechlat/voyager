"""Digital Asset Management (DAM) models.

Provides Asset, AssetFolder, AssetCollection, AssetVersion, AssetLicense,
and AssetUsageLog for centralized storage, organization, versioning, and
usage tracking of digital assets across the Voyager platform.
"""

from __future__ import annotations

import uuid

from django.db import models


class AssetFolder(models.Model):
    """Hierarchical folder structure for organizing assets within a tenant.

    Supports self-referential parent for nested folder trees.
    The ``path`` field stores the full materialized path for efficient
    traversal and display.

    Attributes:
        id: UUID primary key.
        tenant_id: Tenant scope identifier.
        name: Folder display name.
        parent: Optional parent folder for nesting.
        path: Materialized path string (e.g. '/Marketing/2024/Q1').
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    path = models.TextField(default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "asset_folders"
        indexes = [
            models.Index(fields=["tenant_id", "path"]),
            models.Index(fields=["tenant_id", "name"]),
        ]
        ordering = ["path", "name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        """Rebuild materialized path from parent chain on every save."""
        if self.parent:
            parent_path = self.parent.path.rstrip("/")
            self.path = f"{parent_path}/{self.name}"
        else:
            self.path = f"/{self.name}"
        super().save(*args, **kwargs)


class AssetCollection(models.Model):
    """A curated group of assets, optionally with smart-filter rules.

    Static collections store an explicit ordered list of asset IDs.
    Smart collections define filter criteria that dynamically match assets.

    Attributes:
        id: UUID primary key.
        tenant_id: Tenant scope identifier.
        name: Collection display name.
        description: Optional longer description.
        asset_ids: Ordered list of asset UUIDs (for static collections).
        smart_filter: JSON filter criteria (for smart collections).
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    asset_ids = models.JSONField(default=list, blank=True)
    smart_filter = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "asset_collections"
        indexes = [
            models.Index(fields=["tenant_id", "name"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class Asset(models.Model):
    """A digital asset stored in S3-compatible object storage.

    Tracks metadata, thumbnails, tags, dimensions, duration,
    and version info. All assets are scoped to a tenant.

    Attributes:
        id: UUID primary key.
        tenant_id: Tenant scope identifier.
        name: Display name of the asset.
        description: Optional longer description.
        folder: Optional parent folder.
        file_key: S3/MinIO object key (e.g. 'tenant-id/asset-id/filename.jpg').
        file_type: Broad category (image, video, document, audio, font, archive).
        file_size: Size in bytes.
        mime_type: Full MIME type string.
        width: Image/video width in pixels (optional).
        height: Image/video height in pixels (optional).
        duration: Video/audio duration in seconds (optional).
        thumbnail_key: S3 key for generated thumbnail.
        tags: JSON list of AI and user tags.
        metadata: JSON extracted metadata (EXIF for images, etc.).
        dominant_colors: JSON list of dominant color hex values.
        version_number: Current version number.
        usage_count: Number of times the asset has been used.
        last_used_at: Timestamp of most recent usage.
        uploaded_by: UUID of the uploading user.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    class FileType(models.TextChoices):
        """Supported asset file type categories."""

        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        DOCUMENT = "document", "Document"
        AUDIO = "audio", "Audio"
        FONT = "font", "Font"
        ARCHIVE = "archive", "Archive"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    name = models.CharField(max_length=500)
    description = models.TextField(blank=True, default="")
    folder = models.ForeignKey(
        AssetFolder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assets",
    )
    file_key = models.TextField()
    file_type = models.CharField(max_length=20, choices=FileType.choices, db_index=True)
    file_size = models.BigIntegerField(default=0)
    mime_type = models.CharField(max_length=100, blank=True, default="")
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True)
    thumbnail_key = models.TextField(blank=True, default="")
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    dominant_colors = models.JSONField(default=list, blank=True)
    version_number = models.PositiveIntegerField(default=1)
    usage_count = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    uploaded_by = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assets"
        indexes = [
            models.Index(fields=["tenant_id", "file_type"]),
            models.Index(fields=["tenant_id", "created_at"]),
            models.Index(fields=["tenant_id", "uploaded_by"]),
            models.Index(fields=["folder", "tenant_id"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class AssetVersion(models.Model):
    """A historical version of an asset file.

    Created when an asset file is updated. Keeps the previous file_key,
    size, and change notes so the asset can be rolled back.

    Attributes:
        id: UUID primary key.
        asset: Parent asset.
        file_key: S3 object key for this version's file.
        file_size: Size in bytes.
        version_number: Sequential version number.
        change_notes: Description of what changed.
        created_by: UUID of the user who created this version.
        created_at: Creation timestamp.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    file_key = models.TextField()
    file_size = models.BigIntegerField(default=0)
    version_number = models.PositiveIntegerField()
    change_notes = models.TextField(blank=True, default="")
    created_by = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "asset_versions"
        indexes = [
            models.Index(fields=["asset", "-version_number"]),
        ]
        ordering = ["-version_number"]
        unique_together = [["asset", "version_number"]]

    def __str__(self) -> str:
        return f"{self.asset.name} v{self.version_number}"


class AssetLicense(models.Model):
    """Usage-rights and licensing information attached to an asset.

    Tracks license type, holder, validity period, usage rights, and
    restrictions. Enables compliance checking and expiration alerts.

    Attributes:
        id: UUID primary key.
        asset: Parent asset.
        license_type: Type of license (royalty_free, rights_managed, etc.).
        holder: Name of the license holder.
        valid_from: Start of validity period.
        valid_until: End of validity period (null = perpetual).
        usage_rights: JSON dict of permitted uses.
        restrictions: JSON dict of usage restrictions.
        attribution_required: Whether attribution is required.
        attribution_text: Required attribution text.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    class LicenseType(models.TextChoices):
        """Supported license types."""

        ROYALTY_FREE = "royalty_free", "Royalty-Free"
        RIGHTS_MANAGED = "rights_managed", "Rights-Managed"
        EDITORIAL = "editorial", "Editorial"
        CREATIVE_COMMONS = "creative_commons", "Creative Commons"
        CUSTOM = "custom", "Custom"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="licenses",
    )
    license_type = models.CharField(
        max_length=30,
        choices=LicenseType.choices,
        default=LicenseType.ROYALTY_FREE,
    )
    holder = models.CharField(max_length=255, blank=True, default="")
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    usage_rights = models.JSONField(default=dict, blank=True)
    restrictions = models.JSONField(default=dict, blank=True)
    attribution_required = models.BooleanField(default=False)
    attribution_text = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "asset_licenses"
        indexes = [
            models.Index(fields=["asset", "valid_until"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.license_type} — {self.asset.name}"


class AssetUsageLog(models.Model):
    """Log entry recording where and how an asset is used.

    Tracks which module, record, and usage type consumed the asset
    so analytics can report on asset popularity and ROI.

    Attributes:
        id: UUID primary key.
        asset: The asset that was used.
        used_by_module: Name of the consuming module (e.g. 'publishing').
        used_by_record_id: UUID of the record in the consuming module.
        usage_type: Type of usage (e.g. 'embed', 'download', 'reference').
        has_attribution: Whether attribution was included.
        platform: Optional platform name.
        created_at: Usage timestamp.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="usage_logs",
    )
    used_by_module = models.CharField(max_length=50, blank=True, default="")
    used_by_record_id = models.CharField(max_length=128, blank=True, default="")
    usage_type = models.CharField(max_length=50, blank=True, default="")
    has_attribution = models.BooleanField(default=False)
    platform = models.CharField(max_length=50, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "asset_usage_logs"
        indexes = [
            models.Index(fields=["asset", "-created_at"]),
            models.Index(fields=["used_by_module", "used_by_record_id"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.asset.name} — {self.used_by_module}"
