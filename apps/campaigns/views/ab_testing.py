"""A/B testing views.

CRUD for A/B tests, sample size calculation, and results evaluation.
"""

from __future__ import annotations

import logging
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.campaigns.models import CampaignABTest
from apps.campaigns.serializers import (
    ABTestCreateSchema,
    ABTestListSchema,
    ABTestResultSchema,
    ABTestUpdateSchema,
)
from apps.campaigns.services.ab_testing import (
    compute_and_save_sample_size,
    evaluate_test_results,
)

logger = logging.getLogger(__name__)

router = Router()


@router.get("/{campaign_id}/ab-tests", response=list[ABTestListSchema])
def list_ab_tests(
    request,
    campaign_id: int,
    status: str = "",
) -> list[CampaignABTest]:
    """List A/B tests for a campaign.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        status: Filter by status.

    Returns:
        List of A/B tests.
    """
    qs = CampaignABTest.objects.filter(campaign_id=campaign_id)
    if status:
        qs = qs.filter(status=status)
    return list(qs.order_by("-created_at"))


@router.post("/{campaign_id}/ab-tests", response=ABTestListSchema)
def create_ab_test(
    request,
    campaign_id: int,
    payload: ABTestCreateSchema,
) -> CampaignABTest:
    """Create an A/B test for a campaign.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        payload: Test configuration.

    Returns:
        Created A/B test.
    """
    test = CampaignABTest.objects.create(
        campaign_id=campaign_id,
        name=payload.name,
        test_type=payload.test_type,
        method=payload.method,
        significance_level=payload.significance_level,
        power=payload.power,
        baseline_rate=payload.baseline_rate,
        minimum_detectable_effect=payload.minimum_detectable_effect,
        daily_traffic=payload.daily_traffic,
        winner_criteria=payload.winner_criteria,
        variants=payload.variants,
    )

    # Auto-compute sample size if parameters provided
    if payload.baseline_rate and payload.minimum_detectable_effect:
        compute_and_save_sample_size(test)

    logger.info("Created A/B test %s for campaign %s", test.id, campaign_id)
    return test


@router.get("/{campaign_id}/ab-tests/{test_id}")
def get_ab_test(
    request,
    campaign_id: int,
    test_id: int,
) -> dict[str, Any]:
    """Get a single A/B test.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        test_id: Test ID.

    Returns:
        Test details.
    """
    test = get_object_or_404(CampaignABTest, id=test_id, campaign_id=campaign_id)
    return {
        "id": test.id,
        "campaign_id": test.campaign_id,
        "name": test.name,
        "test_type": test.test_type,
        "method": test.method,
        "significance_level": float(test.significance_level),
        "power": float(test.power),
        "sample_size_per_variant": test.sample_size_per_variant,
        "actual_sample_size": test.actual_sample_size,
        "baseline_rate": float(test.baseline_rate) if test.baseline_rate else None,
        "minimum_detectable_effect": (
            float(test.minimum_detectable_effect) if test.minimum_detectable_effect else None
        ),
        "daily_traffic": test.daily_traffic,
        "estimated_duration_days": test.estimated_duration_days,
        "status": test.status,
        "winner_criteria": test.winner_criteria,
        "winner_variant_id": test.winner_variant_id,
        "variants": test.variants,
        "results": test.results,
        "start_date": test.start_date.isoformat() if test.start_date else None,
        "end_date": test.end_date.isoformat() if test.end_date else None,
        "created_at": test.created_at.isoformat(),
        "updated_at": test.updated_at.isoformat(),
    }


@router.put("/{campaign_id}/ab-tests/{test_id}")
def update_ab_test(
    request,
    campaign_id: int,
    test_id: int,
    payload: ABTestUpdateSchema,
) -> dict[str, Any]:
    """Update an A/B test.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        test_id: Test ID.
        payload: Update data.

    Returns:
        Updated test.
    """
    test = get_object_or_404(CampaignABTest, id=test_id, campaign_id=campaign_id)

    for field, value in payload.dict(exclude_unset=True).items():
        if value is not None and hasattr(test, field):
            setattr(test, field, value)

    test.save()
    return {"success": True, "test_id": test_id}


@router.delete("/{campaign_id}/ab-tests/{test_id}")
def delete_ab_test(
    request,
    campaign_id: int,
    test_id: int,
) -> dict[str, Any]:
    """Delete an A/B test.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        test_id: Test ID.

    Returns:
        Deletion confirmation.
    """
    test = get_object_or_404(CampaignABTest, id=test_id, campaign_id=campaign_id)
    test.delete()
    return {"success": True, "deleted_id": test_id}


@router.post("/{campaign_id}/ab-tests/{test_id}/evaluate", response=ABTestResultSchema)
def evaluate_ab_test(
    request,
    campaign_id: int,
    test_id: int,
) -> dict[str, Any]:
    """Evaluate A/B test results.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        test_id: Test ID.

    Returns:
        Evaluation results.
    """
    test = get_object_or_404(CampaignABTest, id=test_id, campaign_id=campaign_id)
    return evaluate_test_results(test)


@router.post("/{campaign_id}/ab-tests/{test_id}/sample-size")
def compute_sample_size(
    request,
    campaign_id: int,
    test_id: int,
    daily_traffic: int | None = None,
) -> dict[str, Any]:
    """Compute sample size for an A/B test.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        test_id: Test ID.
        daily_traffic: Optional daily traffic override.

    Returns:
        Sample size calculation.
    """
    test = get_object_or_404(CampaignABTest, id=test_id, campaign_id=campaign_id)
    result = compute_and_save_sample_size(test, daily_traffic)
    return {"success": True, "test_id": test_id, **result}


@router.post("/{campaign_id}/ab-tests/{test_id}/start")
def start_ab_test(
    request,
    campaign_id: int,
    test_id: int,
) -> dict[str, Any]:
    """Start an A/B test.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        test_id: Test ID.

    Returns:
        Status update.
    """
    from datetime import datetime, timezone

    test = get_object_or_404(CampaignABTest, id=test_id, campaign_id=campaign_id)
    test.status = CampaignABTest.Status.RUNNING
    test.start_date = datetime.now(timezone.utc)
    test.save(update_fields=["status", "start_date", "updated_at"])
    return {"success": True, "status": test.status}


@router.post("/{campaign_id}/ab-tests/{test_id}/stop")
def stop_ab_test(
    request,
    campaign_id: int,
    test_id: int,
) -> dict[str, Any]:
    """Stop/completed an A/B test.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        test_id: Test ID.

    Returns:
        Status update.
    """
    from datetime import datetime, timezone

    test = get_object_or_404(CampaignABTest, id=test_id, campaign_id=campaign_id)
    test.status = CampaignABTest.Status.COMPLETED
    test.end_date = datetime.now(timezone.utc)
    test.save(update_fields=["status", "end_date", "updated_at"])
    return {"success": True, "status": test.status}
