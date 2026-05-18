"""Attribution configuration and calculation views.

Provides endpoints for managing attribution models, running attribution
calculations, and visualizing conversion paths.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.analytics_v2.models.attribution import AttributionModel, ConversionPath, Touchpoint
from apps.analytics_v2.serializers import (
    AttributionCalculateIn,
    AttributionModelCreateIn,
    AttributionModelOut,
    AttributionModelUpdateIn,
    AttributionResultOut,
    ConversionPathOut,
    TouchpointOut,
)
from apps.analytics_v2.services.attribution import (
    calculate_attribution,
    get_attribution_summary,
    visualize_conversion_path,
)
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


def _tenant_from_request(request) -> str:
    """Extract tenant_id from the authenticated request."""
    return getattr(request, "tenant_id", "default")


def _user_from_request(request) -> str:
    """Extract user_id from the authenticated request."""
    user = getattr(request, "auth", None)
    if user and hasattr(user, "sub"):
        return str(user.sub)
    return "anonymous"


# ---------------------------------------------------------------------------
# Attribution Model CRUD
# ---------------------------------------------------------------------------


@router.get("/attribution-models", response=list[AttributionModelOut], tags=["Attribution"])
def list_attribution_models(request) -> list[AttributionModel]:
    """List all attribution models for the current tenant."""
    tenant_id = _tenant_from_request(request)
    return list(AttributionModel.objects.filter(tenant_id=tenant_id))


@router.get("/attribution-models/{model_id}", response=AttributionModelOut, tags=["Attribution"])
def get_attribution_model(request, model_id: UUID) -> AttributionModel:
    """Get a single attribution model."""
    tenant_id = _tenant_from_request(request)
    return get_object_or_404(AttributionModel, id=model_id, tenant_id=tenant_id)


@router.post("/attribution-models", response=AttributionModelOut, tags=["Attribution"])
def create_attribution_model(request, payload: AttributionModelCreateIn) -> AttributionModel:
    """Create a new attribution model configuration."""
    tenant_id = _tenant_from_request(request)
    user_id = _user_from_request(request)

    model = AttributionModel.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        model_type=payload.model_type,
        config=payload.config,
        lookback_window_days=payload.lookback_window_days,
        is_default=payload.is_default,
        created_by=user_id,
    )
    return model


@router.patch("/attribution-models/{model_id}", response=AttributionModelOut, tags=["Attribution"])
def update_attribution_model(
    request, model_id: UUID, payload: AttributionModelUpdateIn
) -> AttributionModel:
    """Update an attribution model."""
    tenant_id = _tenant_from_request(request)
    model = get_object_or_404(AttributionModel, id=model_id, tenant_id=tenant_id)

    for attr in ["name", "model_type", "config", "lookback_window_days", "is_default"]:
        val = getattr(payload, attr, None)
        if val is not None:
            setattr(model, attr, val)
    model.save()
    return model


@router.delete("/attribution-models/{model_id}", tags=["Attribution"])
def delete_attribution_model(request, model_id: UUID) -> dict[str, str]:
    """Delete an attribution model."""
    tenant_id = _tenant_from_request(request)
    model = get_object_or_404(AttributionModel, id=model_id, tenant_id=tenant_id)
    model.delete()
    return {"status": "deleted", "id": str(model_id)}


# ---------------------------------------------------------------------------
# Attribution Calculation
# ---------------------------------------------------------------------------


@router.post("/attribution/calculate", response=AttributionResultOut, tags=["Attribution"])
def calculate_attribution_endpoint(request, payload: AttributionCalculateIn) -> dict[str, Any]:
    """Run attribution calculation on provided conversion paths.

    Applies the specified attribution model to distribute credit across
    touchpoints in the provided conversion journeys.
    """
    tenant_id = _tenant_from_request(request)
    model = get_object_or_404(AttributionModel, id=payload.model_id, tenant_id=tenant_id)

    all_credited = []
    total_conversions = 0
    total_revenue = 0.0

    for cp in payload.conversion_paths:
        touchpoints = cp.get("touchpoints", [])
        conv_date_str = cp.get("conversion_date", datetime.utcnow().isoformat())
        if isinstance(conv_date_str, str):
            conv_date = datetime.fromisoformat(conv_date_str.replace("Z", "+00:00"))
        else:
            conv_date = datetime.utcnow()
        conv_value = float(cp.get("conversion_value", 0))

        credited = calculate_attribution(
            touchpoints,
            conv_date,
            conv_value,
            model.model_type,
            model.config,
        )
        all_credited.extend(credited)
        total_conversions += 1
        total_revenue += conv_value

    summary = get_attribution_summary(all_credited)

    return {
        "model_id": model.id,
        "model_type": model.model_type,
        "total_conversions": total_conversions,
        "total_revenue": round(total_revenue, 2),
        "channel_credits": summary["channel_credits"],
        "touchpoint_credits": [
            {
                "channel": tp.get("channel", ""),
                "platform": tp.get("platform", ""),
                "campaign": tp.get("campaign", ""),
                "credit": round(tp.get("credit", 0), 4),
                "revenue_attributed": round(tp.get("revenue_attributed", 0), 2),
            }
            for tp in all_credited
        ],
    }


@router.post("/attribution/compare", tags=["Attribution"])
def compare_attribution_models(request, payload: dict[str, Any]) -> dict[str, Any]:
    """Compare multiple attribution models side by side.

    Args:
        payload: Dict with model_ids and conversion_paths.

    Returns:
        Comparison results per model.
    """
    tenant_id = _tenant_from_request(request)
    model_ids = payload.get("model_ids", [])
    conversion_paths = payload.get("conversion_paths", [])

    comparisons = {}
    for mid in model_ids:
        try:
            model = AttributionModel.objects.get(id=mid, tenant_id=tenant_id)
        except AttributionModel.DoesNotExist:
            continue

        all_credited = []
        for cp in conversion_paths:
            touchpoints = cp.get("touchpoints", [])
            conv_date_str = cp.get("conversion_date", datetime.utcnow().isoformat())
            conv_date = (
                datetime.fromisoformat(conv_date_str.replace("Z", "+00:00"))
                if isinstance(conv_date_str, str)
                else datetime.utcnow()
            )
            conv_value = float(cp.get("conversion_value", 0))
            credited = calculate_attribution(
                touchpoints, conv_date, conv_value, model.model_type, model.config
            )
            all_credited.extend(credited)

        summary = get_attribution_summary(all_credited)
        comparisons[str(mid)] = {
            "model_name": model.name,
            "model_type": model.model_type,
            "channel_credits": summary["channel_credits"],
            "total_revenue_attributed": summary["total_revenue_attributed"],
        }

    return {"comparisons": comparisons}


# ---------------------------------------------------------------------------
# Conversion Path & Visualization
# ---------------------------------------------------------------------------


@router.get("/conversion-paths", response=list[ConversionPathOut], tags=["Attribution"])
def list_conversion_paths(
    request,
    channel: str = "",
    limit: int = 50,
) -> list[ConversionPath]:
    """List conversion paths for the current tenant."""
    tenant_id = _tenant_from_request(request)
    qs = ConversionPath.objects.filter(tenant_id=tenant_id)
    if channel:
        qs = qs.filter(channel=channel)
    return list(qs[:limit])


@router.get("/conversion-paths/{path_id}", response=ConversionPathOut, tags=["Attribution"])
def get_conversion_path(request, path_id: UUID) -> ConversionPath:
    """Get a single conversion path with its touchpoints."""
    tenant_id = _tenant_from_request(request)
    return get_object_or_404(ConversionPath, id=path_id, tenant_id=tenant_id)


@router.get("/conversion-paths/{path_id}/visualize", tags=["Attribution"])
def visualize_path(request, path_id: UUID) -> dict[str, Any]:
    """Generate visualization data for a conversion path."""
    tenant_id = _tenant_from_request(request)
    cp = get_object_or_404(ConversionPath, id=path_id, tenant_id=tenant_id)

    touchpoints = list(cp.touchpoints.values())
    return visualize_conversion_path(
        touchpoints,
        float(cp.conversion_value),
        cp.conversion_date,
    )


@router.get("/touchpoints", response=list[TouchpointOut], tags=["Attribution"])
def list_touchpoints(
    request,
    channel: str = "",
    platform: str = "",
    limit: int = 100,
) -> list[Touchpoint]:
    """List touchpoints for the current tenant."""
    tenant_id = _tenant_from_request(request)
    qs = Touchpoint.objects.filter(conversion__tenant_id=tenant_id)
    if channel:
        qs = qs.filter(channel=channel)
    if platform:
        qs = qs.filter(platform=platform)
    return list(qs[:limit])


@router.get("/attribution/summary", tags=["Attribution"])
def get_attribution_dashboard_summary(request) -> dict[str, Any]:
    """Get summary statistics for the attribution dashboard."""
    tenant_id = _tenant_from_request(request)

    total_paths = ConversionPath.objects.filter(tenant_id=tenant_id).count()
    total_touchpoints = Touchpoint.objects.filter(conversion__tenant_id=tenant_id).count()

    channel_counts = {}
    for tp in Touchpoint.objects.filter(conversion__tenant_id=tenant_id).values("channel"):
        ch = tp.get("channel", "unknown") or "unknown"
        channel_counts[ch] = channel_counts.get(ch, 0) + 1

    model_count = AttributionModel.objects.filter(tenant_id=tenant_id).count()

    return {
        "total_conversion_paths": total_paths,
        "total_touchpoints": total_touchpoints,
        "avg_touchpoints_per_conversion": (
            round(total_touchpoints / total_paths, 2) if total_paths > 0 else 0
        ),
        "channel_distribution": channel_counts,
        "attribution_models_configured": model_count,
    }
