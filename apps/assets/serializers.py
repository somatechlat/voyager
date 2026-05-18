"""Ninja schemas (serializers) for the Assets (DAM) module.

Provides input and output schemas for all API endpoints including
assets, folders, collections, versions, licenses, and usage logs.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from ninja import Schema

# ---------------------------------------------------------------------------
# Base schemas
# ---------------------------------------------------------------------------


class AssetFolderIn(Schema):
    """Input schema for creating or updating a folder."""

    name: str
    parent_id: UUID | None = None


class AssetFolderOut(Schema):
    """Output schema for a folder."""

    id: UUID
    tenant_id: str
    name: str
    parent_id: UUID | None
    path: str
    created_at: datetime
    updated_at: datetime


class AssetFolderTreeOut(Schema):
    """Output schema for a folder tree node."""

    id: UUID
    name: str
    path: str
    parent_id: UUID | None
    children: list[dict[str, Any]]


class AssetCollectionIn(Schema):
    """Input schema for creating or updating a collection."""

    name: str
    description: str = ""
    asset_ids: list[UUID] = []
    smart_filter: dict[str, Any] = {}


class AssetCollectionOut(Schema):
    """Output schema for a collection."""

    id: UUID
    tenant_id: str
    name: str
    description: str
    asset_ids: list[UUID]
    smart_filter: dict[str, Any]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Asset schemas
# ---------------------------------------------------------------------------


class AssetIn(Schema):
    """Input schema for creating an asset record (after upload)."""

    name: str
    description: str = ""
    folder_id: UUID | None = None
    file_type: str
    file_size: int = 0
    mime_type: str = ""
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    tags: list[str] = []
    metadata: dict[str, Any] = {}
    dominant_colors: list[str] = []


class AssetUpdateIn(Schema):
    """Input schema for updating an asset."""

    name: str | None = None
    description: str | None = None
    folder_id: UUID | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class AssetOut(Schema):
    """Output schema for an asset."""

    id: UUID
    tenant_id: str
    name: str
    description: str
    folder_id: UUID | None
    file_key: str
    file_type: str
    file_size: int
    mime_type: str
    width: int | None
    height: int | None
    duration: float | None
    thumbnail_key: str
    tags: list[str]
    metadata: dict[str, Any]
    dominant_colors: list[str]
    version_number: int
    usage_count: int
    last_used_at: datetime | None
    uploaded_by: str
    created_at: datetime
    updated_at: datetime


class AssetUploadResponse(Schema):
    """Response schema for a file upload."""

    id: UUID
    name: str
    file_key: str
    file_type: str
    file_size: int
    mime_type: str
    thumbnail_key: str
    presigned_url: str | None


class AssetBulkUploadItem(Schema):
    """Single item in a bulk upload request."""

    filename: str
    content_type: str
    file_size: int
    folder_id: UUID | None = None


class AssetBulkUploadResponse(Schema):
    """Response schema for bulk upload request."""

    presigned_posts: list[dict[str, Any]]
    asset_ids: list[UUID]


class AssetSearchFilters(Schema):
    """Query parameters for asset search."""

    file_type: str | None = None
    folder_id: UUID | None = None
    uploaded_by: str | None = None
    tags: list[str] = []
    search: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


# ---------------------------------------------------------------------------
# Version schemas
# ---------------------------------------------------------------------------


class AssetVersionIn(Schema):
    """Input for creating a version snapshot."""

    change_notes: str = ""


class AssetVersionOut(Schema):
    """Output schema for a version."""

    id: UUID
    asset_id: UUID
    file_key: str
    file_size: int
    version_number: int
    change_notes: str
    created_by: str
    created_at: datetime


class AssetVersionDiffOut(Schema):
    """Output schema for a version comparison."""

    type: str
    changes: list[dict[str, Any]]
    metadata: dict[str, Any] | None = None


class AssetRollbackIn(Schema):
    """Input for rolling back to a previous version."""

    version_number: int


# ---------------------------------------------------------------------------
# License schemas
# ---------------------------------------------------------------------------


class AssetLicenseIn(Schema):
    """Input schema for creating a license."""

    license_type: str
    holder: str = ""
    valid_from: date | None = None
    valid_until: date | None = None
    usage_rights: dict[str, Any] = {}
    restrictions: dict[str, Any] = {}
    attribution_required: bool = False
    attribution_text: str = ""


class AssetLicenseUpdateIn(Schema):
    """Input schema for updating a license."""

    license_type: str | None = None
    holder: str | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    usage_rights: dict[str, Any] | None = None
    restrictions: dict[str, Any] | None = None
    attribution_required: bool | None = None
    attribution_text: str | None = None


class AssetLicenseOut(Schema):
    """Output schema for a license."""

    id: UUID
    asset_id: UUID
    license_type: str
    holder: str
    valid_from: date | None
    valid_until: date | None
    usage_rights: dict[str, Any]
    restrictions: dict[str, Any]
    attribution_required: bool
    attribution_text: str
    created_at: datetime
    updated_at: datetime


class AssetLicenseComplianceOut(Schema):
    """Output schema for license compliance check."""

    status: str
    score: int
    grade: str
    days_until_expiry: int | None
    warnings: list[dict[str, Any]]
    license: dict[str, Any]


class AssetLicenseAlertOut(Schema):
    """Output schema for license alerts."""

    expiring: list[dict[str, Any]]
    expired: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Usage schemas
# ---------------------------------------------------------------------------


class AssetUsageLogIn(Schema):
    """Input for logging an asset usage event."""

    used_by_module: str
    used_by_record_id: str = ""
    usage_type: str = ""
    has_attribution: bool = False
    platform: str = ""


class AssetUsageLogOut(Schema):
    """Output schema for a usage log entry."""

    id: UUID
    asset_id: UUID
    used_by_module: str
    used_by_record_id: str
    usage_type: str
    has_attribution: bool
    platform: str
    created_at: datetime


class AssetUsageStatsOut(Schema):
    """Output schema for asset usage statistics."""

    asset_id: UUID
    total_usage: int
    by_module: dict[str, int]
    by_type: dict[str, int]


class TenantAnalyticsOut(Schema):
    """Output schema for tenant-wide analytics."""

    period_days: int
    total_assets: int
    used_assets: int
    unused_assets: int
    storage_used_bytes: int
    storage_used_mb: float
    top_assets: list[dict[str, Any]]
    recently_used: list[dict[str, Any]]
    usage_by_module: dict[str, int]
    usage_by_type: dict[str, int]
    upload_trend: list[dict[str, Any]]
