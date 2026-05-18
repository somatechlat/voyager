"""Assets services package.

Business logic for digital asset management:
- storage: S3/MinIO upload, download, presigned URLs
- organization: Folder CRUD, collections, smart folders
- versioning: Version control, diff, rollback
- licensing: License tracking, expiration alerts, compliance
- analytics: Usage stats, performance metrics
"""

from __future__ import annotations

from .analytics import AnalyticsService
from .licensing import LicensingService
from .organization import OrganizationService
from .storage import StorageService
from .versioning import VersioningService

__all__ = [
    "AnalyticsService",
    "LicensingService",
    "OrganizationService",
    "StorageService",
    "VersioningService",
]
