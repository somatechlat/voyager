"""OKR Tracking views — SP-005.

CRUD endpoints, hierarchical tree view, progress calculation,
and confidence summary.
"""

from __future__ import annotations

import logging
from typing import Any

from ninja import Query, Router

from apps.strategy.models.okr import KeyResult, Objective
from apps.strategy.serializers.okr import (
    ConfidenceSummaryOut,
    KeyResultIn,
    KeyResultOut,
    ObjectiveIn,
    ObjectiveOut,
    ObjectiveTreeOut,
    OKRFilter,
    ProgressOut,
    ProgressUpdateIn,
)
from apps.strategy.services.okr import OKRService

logger = logging.getLogger(__name__)

router = Router(tags=["Strategy / OKR"])


def _get_tenant_id(request) -> str:
    return getattr(request, "tenant_id", "default")


def _objective_to_dict(o: Objective) -> dict[str, Any]:
    return {
        "id": str(o.id),
        "title": o.title,
        "level": o.level,
        "quarter": o.quarter,
        "status": o.status,
        "progress": o.progress,
        "description": o.description or "",
        "team_id": str(o.team_id) if o.team_id else None,
        "owner_id": str(o.owner_id),
        "parent_id": str(o.parent_id) if o.parent_id else None,
        "created_at": o.created_at,
        "updated_at": o.updated_at,
    }


def _key_result_to_dict(kr: KeyResult) -> dict[str, Any]:
    return {
        "id": str(kr.id),
        "objective_id": str(kr.objective_id),
        "title": kr.title,
        "kr_type": kr.kr_type,
        "target_value": kr.target_value,
        "current_value": kr.current_value,
        "start_value": kr.start_value,
        "direction": kr.direction,
        "unit": kr.unit or "",
        "progress": kr.progress,
        "confidence": kr.confidence,
        "data_source": kr.data_source or {},
        "created_at": kr.created_at,
        "updated_at": kr.updated_at,
    }


# ---------------------------------------------------------------------------
# Objectives
# ---------------------------------------------------------------------------

@router.post("/objectives", response=ObjectiveOut)
def create_objective(request, payload: ObjectiveIn):
    """Create an OKR objective."""
    tenant_id = _get_tenant_id(request)
    obj = OKRService.create_objective(
        tenant_id=tenant_id,
        title=payload.title,
        level=payload.level,
        owner_id=payload.owner_id,
        quarter=payload.quarter,
        description=payload.description,
        parent_id=payload.parent_id,
        team_id=payload.team_id,
    )
    return _objective_to_dict(obj)


@router.get("/objectives", response=list[ObjectiveOut])
def list_objectives(request, filters: Query[OKRFilter]):
    """List objectives for the tenant."""
    tenant_id = _get_tenant_id(request)
    qs = Objective.objects.filter(tenant_id=tenant_id)
    if filters.quarter:
        qs = qs.filter(quarter=filters.quarter)
    if filters.level:
        qs = qs.filter(level=filters.level)
    if filters.status:
        qs = qs.filter(status=filters.status)
    if filters.owner_id:
        qs = qs.filter(owner_id=filters.owner_id)
    qs = qs.order_by("-created_at")[filters.offset : filters.offset + filters.limit]
    return [_objective_to_dict(o) for o in qs]


@router.get("/objectives/{objective_id}", response=ObjectiveOut)
def get_objective(request, objective_id: str):
    """Get a single objective."""
    tenant_id = _get_tenant_id(request)
    obj = Objective.objects.get(id=objective_id, tenant_id=tenant_id)
    return _objective_to_dict(obj)


@router.put("/objectives/{objective_id}", response=ObjectiveOut)
def update_objective(request, objective_id: str, payload: ObjectiveIn):
    """Update an objective."""
    tenant_id = _get_tenant_id(request)
    obj = Objective.objects.get(id=objective_id, tenant_id=tenant_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    obj.save()
    return _objective_to_dict(obj)


@router.delete("/objectives/{objective_id}")
def delete_objective(request, objective_id: str):
    """Delete an objective and all its key results (cascade)."""
    tenant_id = _get_tenant_id(request)
    obj = Objective.objects.get(id=objective_id, tenant_id=tenant_id)
    obj.delete()
    return {"success": True, "id": str(objective_id), "action": "deleted"}


# ---------------------------------------------------------------------------
# Key Results
# ---------------------------------------------------------------------------

@router.post("/objectives/{objective_id}/key-results", response=KeyResultOut)
def create_key_result(request, objective_id: str, payload: KeyResultIn):
    """Create a key result under an objective."""
    kr = OKRService.create_key_result(
        objective_id=objective_id,
        title=payload.title,
        kr_type=payload.kr_type,
        target_value=payload.target_value,
        start_value=payload.start_value,
        current_value=payload.current_value,
        direction=payload.direction,
        unit=payload.unit,
        data_source=payload.data_source,
    )
    return _key_result_to_dict(kr)


@router.get("/key-results/{key_result_id}", response=KeyResultOut)
def get_key_result(request, key_result_id: str):
    """Get a single key result."""
    kr = KeyResult.objects.get(id=key_result_id)
    tenant_id = _get_tenant_id(request)
    if kr.objective.tenant_id != tenant_id:
        raise KeyResult.DoesNotExist("KeyResult not found in tenant scope")
    return _key_result_to_dict(kr)


@router.put("/key-results/{key_result_id}", response=KeyResultOut)
def update_key_result(request, key_result_id: str, payload: KeyResultIn):
    """Update a key result."""
    tenant_id = _get_tenant_id(request)
    kr = KeyResult.objects.get(id=key_result_id)
    if kr.objective.tenant_id != tenant_id:
        raise KeyResult.DoesNotExist("KeyResult not found in tenant scope")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(kr, field, value)
    kr.save()
    return _key_result_to_dict(kr)


@router.delete("/key-results/{key_result_id}")
def delete_key_result(request, key_result_id: str):
    """Delete a key result."""
    tenant_id = _get_tenant_id(request)
    kr = KeyResult.objects.get(id=key_result_id)
    if kr.objective.tenant_id != tenant_id:
        raise KeyResult.DoesNotExist("KeyResult not found in tenant scope")
    kr.delete()
    return {"success": True, "id": str(key_result_id), "action": "deleted"}


# ---------------------------------------------------------------------------
# Progress Tracking
# ---------------------------------------------------------------------------

@router.post("/key-results/{key_result_id}/progress", response=ProgressOut)
def update_progress(request, key_result_id: str, payload: ProgressUpdateIn):
    """Update key result progress with a new current value."""
    return OKRService.update_progress(
        key_result_id=key_result_id,
        current_value=payload.current_value,
    )


@router.get("/key-results/{key_result_id}/progress", response=ProgressOut)
def get_progress(request, key_result_id: str):
    """Get current progress for a key result."""
    kr = KeyResult.objects.get(id=key_result_id)
    result = kr.calculate_progress()
    return {
        "progress": result["progress"],
        "progressPercent": result["progressPercent"],
        "currentValue": result["currentValue"],
        "targetValue": result["targetValue"],
        "confidence": result["confidence"],
        "velocity": result["velocity"],
        "projectedCompletion": result["projectedCompletion"],
    }


# ---------------------------------------------------------------------------
# Objective Tree
# ---------------------------------------------------------------------------

@router.get("/objectives/tree", response=list[ObjectiveTreeOut])
def get_objective_tree(request, quarter: str | None = None):
    """Get full OKR hierarchy with nested children and key results."""
    tenant_id = _get_tenant_id(request)
    return OKRService.get_objective_tree(tenant_id=tenant_id, quarter=quarter)


# ---------------------------------------------------------------------------
# Confidence Summary
# ---------------------------------------------------------------------------

@router.get("/okrs/confidence-summary", response=ConfidenceSummaryOut)
def confidence_summary(request, quarter: str | None = None):
    """Get confidence summary across all OKRs."""
    tenant_id = _get_tenant_id(request)
    return OKRService.get_confidence_summary(tenant_id=tenant_id, quarter=quarter)


# ---------------------------------------------------------------------------
# Data Source Sync
# ---------------------------------------------------------------------------

@router.post("/key-results/{key_result_id}/sync")
def sync_data_source(request, key_result_id: str, value: float):
    """Sync a key result from an external data source."""
    return OKRService.sync_data_source(
        key_result_id=key_result_id,
        value=value,
    )
