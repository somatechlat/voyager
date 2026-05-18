"""Usage and analytics endpoints — logging, stats, and reports."""

from __future__ import annotations

import uuid

from ninja import Router

from apps.assets.models import Asset
from apps.assets.serializers import (
    AssetUsageLogIn,
    AssetUsageLogOut,
    AssetUsageStatsOut,
    TenantAnalyticsOut,
)
from apps.assets.services.analytics import AnalyticsService
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


def _get_tenant_id(request) -> str:
    return getattr(request, "tenant_id", "default")


@router.get("/assets/{asset_id}/usage", response=AssetUsageStatsOut, tags=["Assets"])
def get_usage_stats(request, asset_id: uuid.UUID):
    """Get usage statistics for an asset."""
    return AnalyticsService.get_usage_stats(str(asset_id))


@router.post("/assets/{asset_id}/usage", response=AssetUsageLogOut, tags=["Assets"])
def log_usage(request, asset_id: uuid.UUID, payload: AssetUsageLogIn):
    """Log a usage event for an asset."""
    tenant_id = _get_tenant_id(request)
    asset = Asset.objects.get(tenant_id=tenant_id, id=asset_id)
    return AnalyticsService.log_usage(
        asset=asset,
        used_by_module=payload.used_by_module,
        used_by_record_id=payload.used_by_record_id,
        usage_type=payload.usage_type,
        has_attribution=payload.has_attribution,
        platform=payload.platform,
    )


@router.get("/assets/analytics/dashboard", response=TenantAnalyticsOut, tags=["Assets"])
def tenant_analytics(request, days: int = 30):
    """Get tenant-wide asset analytics."""
    tenant_id = _get_tenant_id(request)
    return AnalyticsService.get_tenant_analytics(tenant_id, days)


@router.get("/assets/analytics/tags", tags=["Assets"])
def popular_tags(request, limit: int = 50):
    """Get popular tags across the tenant's assets."""
    tenant_id = _get_tenant_id(request)
    return {"tags": AnalyticsService.get_popular_tags(tenant_id, limit)}
