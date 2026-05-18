"""OKR Tracking service — SP-005 business logic.

Handles objective/key result CRUD, hierarchical alignment, progress
calculation, and confidence scoring.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from apps.strategy.models.okr import KeyResult, Objective

logger = logging.getLogger(__name__)


class OKRService:
    """Service for OKR tracking operations."""

    @staticmethod
    def create_objective(
        tenant_id: str,
        title: str,
        level: str,
        owner_id: str,
        quarter: str,
        description: str = "",
        parent_id: str | None = None,
        team_id: str | None = None,
    ) -> Objective:
        """Create an OKR objective.

        Args:
            tenant_id: Tenant scope.
            title: Objective title.
            level: Scope level (company/team/individual).
            owner_id: Owner UUID.
            quarter: Quarter (e.g. '2026-Q2').
            description: Detailed description.
            parent_id: Parent objective UUID.
            team_id: Team UUID (for team-level).

        Returns:
            Created Objective.
        """
        obj = Objective.objects.create(
            tenant_id=tenant_id,
            title=title,
            level=level,
            owner_id=owner_id,
            quarter=quarter,
            description=description,
            parent_id=parent_id if parent_id else None,
            team_id=team_id if team_id else None,
        )
        logger.info("Created objective %s for tenant %s", obj.id, tenant_id)
        return obj

    @staticmethod
    def create_key_result(
        objective_id: str,
        title: str,
        kr_type: str,
        target_value: float,
        start_value: float = 0,
        current_value: float = 0,
        direction: str = "increase",
        unit: str = "",
        data_source: dict[str, Any] | None = None,
    ) -> KeyResult:
        """Create a key result.

        Args:
            objective_id: Parent objective UUID.
            title: Key result title.
            kr_type: Type (numeric/percentage/binary).
            target_value: Target.
            start_value: Baseline.
            current_value: Current measured value.
            direction: 'increase' or 'decrease'.
            unit: Measurement unit.
            data_source: Automated data source config.

        Returns:
            Created KeyResult.
        """
        kr = KeyResult.objects.create(
            objective_id=objective_id,
            title=title,
            kr_type=kr_type,
            target_value=target_value,
            start_value=start_value,
            current_value=current_value,
            direction=direction,
            unit=unit,
            data_source=data_source or {},
        )
        logger.info("Created key result %s under objective %s", kr.id, objective_id)
        return kr

    @staticmethod
    def update_progress(
        key_result_id: str,
        current_value: float,
    ) -> dict[str, Any]:
        """Update a key result's current value and recalculate.

        Args:
            key_result_id: Key result UUID.
            current_value: New measured value.

        Returns:
            Progress calculation result.
        """
        kr = KeyResult.objects.get(id=key_result_id)
        kr.current_value = current_value
        kr.save(update_fields=["current_value", "updated_at"])

        result = kr.calculate_progress()

        # Cascade to parent objective
        if kr.objective:
            kr.objective.recalculate_progress()
            kr.objective.save(update_fields=["progress", "status", "updated_at"])
            result["objective_progress"] = float(kr.objective.progress)
            result["objective_status"] = kr.objective.status

        logger.info("Updated KR %s progress: %s%%", key_result_id, result["progressPercent"])
        return result

    @staticmethod
    def get_objective_tree(
        tenant_id: str,
        quarter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get the full OKR hierarchy for a tenant.

        Args:
            tenant_id: Tenant scope.
            quarter: Optional quarter filter.

        Returns:
            List of top-level objectives with nested children and KRs.
        """
        qs = Objective.objects.filter(
            tenant_id=tenant_id,
            parent__isnull=True,
        )
        if quarter:
            qs = qs.filter(quarter=quarter)

        objectives = qs.select_related().prefetch_related("key_results")
        return [OKRService._serialize_objective(o, depth=0) for o in objectives]

    @staticmethod
    def _serialize_objective(
        obj: Objective,
        depth: int = 0,
    ) -> dict[str, Any]:
        """Serialize an objective with children and key results."""
        krs = []
        for kr in obj.key_results.all():
            krs.append(
                {
                    "id": str(kr.id),
                    "title": kr.title,
                    "kr_type": kr.kr_type,
                    "target_value": float(kr.target_value),
                    "current_value": float(kr.current_value),
                    "start_value": float(kr.start_value),
                    "direction": kr.direction,
                    "unit": kr.unit,
                    "progress": float(kr.progress),
                    "confidence": kr.confidence,
                    "data_source": kr.data_source,
                }
            )

        children = [
            OKRService._serialize_objective(child, depth=depth + 1) for child in obj.children.all()
        ]

        return {
            "id": str(obj.id),
            "title": obj.title,
            "level": obj.level,
            "quarter": obj.quarter,
            "status": obj.status,
            "progress": float(obj.progress),
            "description": obj.description,
            "team_id": str(obj.team_id) if obj.team_id else None,
            "owner_id": str(obj.owner_id),
            "key_results": krs,
            "children": children,
            "depth": depth,
        }

    @staticmethod
    def get_confidence_summary(tenant_id: str, quarter: str | None = None) -> dict[str, Any]:
        """Get confidence summary across all OKRs.

        Args:
            tenant_id: Tenant scope.
            quarter: Optional quarter filter.

        Returns:
            Summary with on_track, at_risk counts and average progress.
        """
        from django.db.models import Avg, Count

        qs = Objective.objects.filter(tenant_id=tenant_id)
        if quarter:
            qs = qs.filter(quarter=quarter)

        by_status = qs.values("status").annotate(count=Count("id"))
        avg_progress = qs.aggregate(avg=Avg("progress"))["avg"]

        summary = {s[0]: 0 for s in Objective.Status.choices}
        for bs in by_status:
            summary[bs["status"]] = bs["count"]

        return {
            "objectives_by_status": summary,
            "total_objectives": sum(summary.values()),
            "average_progress": round(float(avg_progress or 0), 4),
        }

    @staticmethod
    def sync_data_source(
        key_result_id: str,
        value: float,
    ) -> dict[str, Any]:
        """Sync a key result from an external data source.

        Args:
            key_result_id: Key result UUID.
            value: Fetched value from external system.

        Returns:
            Updated progress dict.
        """
        kr = KeyResult.objects.get(id=key_result_id)
        kr.current_value = value
        kr.save(update_fields=["current_value", "updated_at"])

        # Update data source last sync
        ds = kr.data_source or {}
        ds["last_sync"] = date.today().isoformat()
        kr.data_source = ds
        kr.save(update_fields=["data_source"])

        return OKRService.update_progress(key_result_id, value)
