"""Analytics service for asset usage statistics and performance metrics.

Tracks asset consumption across modules, generates usage reports,
and identifies popular and unused assets.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from django.db.models import Count, Sum

from apps.assets.models import Asset, AssetUsageLog

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for asset usage analytics and reporting."""

    @staticmethod
    def log_usage(
        asset: Asset,
        used_by_module: str,
        used_by_record_id: str = "",
        usage_type: str = "",
        has_attribution: bool = False,
        platform: str = "",
    ) -> AssetUsageLog:
        """Record a usage event for an asset.

        Increments the asset's usage_count and updates last_used_at.

        Args:
            asset: The asset being used.
            used_by_module: Name of the consuming module.
            used_by_record_id: UUID of the record in the consuming module.
            usage_type: Type of usage (embed, download, reference).
            has_attribution: Whether attribution was included.
            platform: Optional platform name.

        Returns:
            The created usage log entry.
        """
        log_entry = AssetUsageLog.objects.create(
            asset=asset,
            used_by_module=used_by_module,
            used_by_record_id=used_by_record_id,
            usage_type=usage_type,
            has_attribution=has_attribution,
            platform=platform,
        )
        asset.usage_count += 1
        asset.last_used_at = log_entry.created_at
        asset.save(update_fields=["usage_count", "last_used_at"])
        return log_entry

    @staticmethod
    def get_usage_log(
        asset_id: str,
        limit: int = 50,
    ) -> list[AssetUsageLog]:
        """Retrieve recent usage log entries for an asset.

        Args:
            asset_id: UUID of the asset.
            limit: Maximum number of entries.

        Returns:
            List of usage log entries.
        """
        return list(AssetUsageLog.objects.filter(asset_id=asset_id).order_by("-created_at")[:limit])

    @staticmethod
    def get_usage_stats(asset_id: str) -> dict[str, Any]:
        """Get aggregate usage statistics for a single asset.

        Args:
            asset_id: UUID of the asset.

        Returns:
            Dict with total usage and breakdowns by module and type.
        """
        logs = AssetUsageLog.objects.filter(asset_id=asset_id)
        total = logs.count()
        by_module = dict(
            logs.values("used_by_module")
            .annotate(count=Count("id"))
            .values_list("used_by_module", "count")
        )
        by_type = dict(
            logs.values("usage_type").annotate(count=Count("id")).values_list("usage_type", "count")
        )
        return {
            "asset_id": asset_id,
            "total_usage": total,
            "by_module": by_module,
            "by_type": by_type,
        }

    @staticmethod
    def get_tenant_analytics(
        tenant_id: str,
        days: int = 30,
    ) -> dict[str, Any]:
        """Generate a comprehensive analytics report for a tenant.

        Args:
            tenant_id: Tenant scope identifier.
            days: Look-back period in days.

        Returns:
            Dict with total assets, used/unused counts, top assets,
            storage used, and usage by module.
        """
        cutoff = datetime.now() - timedelta(days=days)
        assets = Asset.objects.filter(tenant_id=tenant_id)

        total_assets = assets.count()
        used_assets = assets.filter(usage_count__gt=0).count()
        unused_assets = assets.filter(
            usage_count=0,
            created_at__lt=datetime.now() - timedelta(days=30),
        ).count()
        storage_used = assets.aggregate(total=Sum("file_size")).get("total") or 0

        top_assets = list(
            assets.filter(usage_count__gt=0)
            .order_by("-usage_count")
            .values("id", "name", "file_type", "usage_count")[:20]
        )
        recently_used = list(
            assets.filter(last_used_at__isnull=False)
            .order_by("-last_used_at")
            .values("id", "name", "file_type", "last_used_at")[:20]
        )

        # Usage by module in the period
        module_usage = dict(
            AssetUsageLog.objects.filter(
                asset__tenant_id=tenant_id,
                created_at__gte=cutoff,
            )
            .values("used_by_module")
            .annotate(count=Count("id"))
            .values_list("used_by_module", "count")
        )

        # Usage by file type
        type_usage = dict(
            Asset.objects.filter(tenant_id=tenant_id, usage_count__gt=0)
            .values("file_type")
            .annotate(count=Count("id"))
            .values_list("file_type", "count")
        )

        # Upload trend: count per day for the period
        recent_uploads = list(
            Asset.objects.filter(
                tenant_id=tenant_id,
                created_at__gte=cutoff,
            )
            .extra(select={"day": "date(created_at)"})
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        return {
            "period_days": days,
            "total_assets": total_assets,
            "used_assets": used_assets,
            "unused_assets": unused_assets,
            "storage_used_bytes": storage_used,
            "storage_used_mb": round(storage_used / (1024 * 1024), 2),
            "top_assets": top_assets,
            "recently_used": recently_used,
            "usage_by_module": module_usage,
            "usage_by_type": type_usage,
            "upload_trend": [{"date": str(r["day"]), "count": r["count"]} for r in recent_uploads],
        }

    @staticmethod
    def get_popular_tags(tenant_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Extract and rank tags by frequency across a tenant's assets.

        Args:
            tenant_id: Tenant scope identifier.
            limit: Maximum number of tags to return.

        Returns:
            List of dicts with ``tag`` and ``count``.
        """
        tag_counts: dict[str, int] = {}
        assets = Asset.objects.filter(tenant_id=tenant_id)
        for asset in assets.iterator():
            for tag in asset.tags or []:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        sorted_tags = sorted(
            [{"tag": k, "count": v} for k, v in tag_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )
        return sorted_tags[:limit]
