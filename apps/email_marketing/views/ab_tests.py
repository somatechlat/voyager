"""A/B testing management views."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.email_marketing.models.ab_test import EmailABTest
from apps.email_marketing.serializers import (
    ABTestResultSchema,
    EmailABTestCreateSchema,
    EmailABTestDetailSchema,
    EmailABTestListSchema,
    EmailABTestUpdateSchema,
    SampleSizeCalcSchema,
    WinnerSelectSchema,
)
from apps.email_marketing.services.ab_testing import (
    calculate_lift,
    calculate_sample_size,
    chi_squared_test,
    select_winner,
)

logger = logging.getLogger(__name__)

router = Router()


@router.get("/", response=list[EmailABTestListSchema])
def list_ab_tests(
    request,
    tenant_id: str = "",
    test_type: str = "",
    status: str = "",
    search: str = "",
    limit: int = 50,
    offset: int = 0,
) -> list[EmailABTest]:
    """List A/B tests with optional filtering.

    Args:
        request: HTTP request.
        tenant_id: Filter by tenant.
        test_type: Filter by test type.
        status: Filter by status.
        search: Search in name.
        limit: Page size.
        offset: Pagination offset.

    Returns:
        List of A/B tests.
    """
    qs = EmailABTest.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if test_type:
        qs = qs.filter(test_type=test_type)
    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(name__icontains=search)
    return list(qs.order_by("-created_at")[offset : offset + limit])


@router.post("/", response=EmailABTestDetailSchema)
def create_ab_test(
    request,
    payload: EmailABTestCreateSchema,
) -> EmailABTest:
    """Create a new A/B test.

    Args:
        request: HTTP request.
        payload: A/B test creation data.

    Returns:
        Created A/B test.
    """
    data = payload.dict()
    ab_test = EmailABTest.objects.create(**data)
    logger.info("A/B test %s created for tenant %s", ab_test.id, ab_test.tenant_id)
    return ab_test


@router.get("/{test_id}", response=EmailABTestDetailSchema)
def get_ab_test(
    request,
    test_id: int,
) -> EmailABTest:
    """Get a single A/B test.

    Args:
        request: HTTP request.
        test_id: A/B test primary key.

    Returns:
        A/B test.
    """
    return get_object_or_404(EmailABTest, id=test_id)


@router.put("/{test_id}", response=EmailABTestDetailSchema)
def update_ab_test(
    request,
    test_id: int,
    payload: EmailABTestUpdateSchema,
) -> EmailABTest:
    """Update an A/B test.

    Args:
        request: HTTP request.
        test_id: A/B test primary key.
        payload: Update data.

    Returns:
        Updated A/B test.
    """
    ab_test = get_object_or_404(EmailABTest, id=test_id)
    data = payload.dict(exclude_unset=True)
    for attr, val in data.items():
        setattr(ab_test, attr, val)
    ab_test.save()
    return ab_test


@router.delete("/{test_id}")
def delete_ab_test(
    request,
    test_id: int,
) -> dict[str, bool]:
    """Delete an A/B test.

    Args:
        request: HTTP request.
        test_id: A/B test primary key.

    Returns:
        Success dict.
    """
    ab_test = get_object_or_404(EmailABTest, id=test_id)
    ab_test.delete()
    return {"success": True}


@router.post("/sample-size")
def sample_size_calc(
    request,
    payload: SampleSizeCalcSchema,
) -> dict[str, Any]:
    """Calculate required sample size for an A/B test.

    Args:
        request: HTTP request.
        payload: Calculation parameters.

    Returns:
        Sample size result.
    """
    result = calculate_sample_size(
        baseline_rate=payload.baseline_rate,
        mde=payload.mde,
        confidence=payload.confidence,
        power=payload.power,
    )
    if payload.list_size:
        total = result.get("total_sample", 0)
        if total > payload.list_size * 0.5:
            result["warning"] = "Sample size exceeds 50% of list. Reduce MDE or increase list."
    return result


@router.post("/{test_id}/select-winner")
def select_winner_endpoint(
    request,
    test_id: int,
    payload: WinnerSelectSchema,
) -> dict[str, Any]:
    """Select the winning variant from A/B test results.

    Args:
        request: HTTP request.
        test_id: A/B test primary key.
        payload: Winner selection parameters.

    Returns:
        Winner selection result.
    """
    ab_test = get_object_or_404(EmailABTest, id=test_id)
    metric = payload.metric or ab_test.winning_metric
    result = select_winner(
        variants=payload.variants,
        metric=metric,
        confidence_level=ab_test.confidence_level,
    )
    if result["winner"] and result["significant"]:
        ab_test.winner_variant_id = result["winner"].get("id", "")
        ab_test.winner_selected_at = datetime.now(UTC)
        ab_test.status = EmailABTest.Status.WINNER_SELECTED
        ab_test.save(update_fields=["winner_variant_id", "winner_selected_at", "status"])
    return result


@router.post("/{test_id}/deploy-winner")
def deploy_winner(
    request,
    test_id: int,
) -> dict[str, Any]:
    """Deploy the winning variant as a full campaign.

    Args:
        request: HTTP request.
        test_id: A/B test primary key.

    Returns:
        Deploy result.
    """
    ab_test = get_object_or_404(EmailABTest, id=test_id)
    if not ab_test.winner_variant_id:
        return {"success": False, "error": "No winner selected yet"}
    if ab_test.status != EmailABTest.Status.WINNER_SELECTED:
        return {"success": False, "error": f"Cannot deploy in status: {ab_test.status}"}
    ab_test.status = EmailABTest.Status.DEPLOYED
    ab_test.completed_at = datetime.now(UTC)
    ab_test.save(update_fields=["status", "completed_at"])
    return {
        "success": True,
        "test_id": str(ab_test.id),
        "winner_variant_id": ab_test.winner_variant_id,
        "deployed_at": ab_test.completed_at.isoformat(),
    }


@router.post("/{test_id}/chi-square")
def chi_square_test(
    request,
    test_id: int,
    payload: ABTestResultSchema,
) -> dict[str, Any]:
    """Run chi-squared test on two variants.

    Args:
        request: HTTP request.
        test_id: A/B test primary key.
        payload: Variant data.

    Returns:
        Chi-squared test result.
    """
    return chi_squared_test(
        control_conversions=payload.control_conversions,
        control_total=payload.control_total,
        variant_conversions=payload.variant_conversions,
        variant_total=payload.variant_total,
    )


@router.post("/{test_id}/lift")
def lift_calc(
    request,
    test_id: int,
    payload: ABTestResultSchema,
) -> dict[str, Any]:
    """Calculate lift between control and variant.

    Args:
        request: HTTP request.
        test_id: A/B test primary key.
        payload: Variant data.

    Returns:
        Lift calculation result.
    """
    control_rate = (
        payload.control_conversions / payload.control_total if payload.control_total > 0 else 0.0
    )
    variant_rate = (
        payload.variant_conversions / payload.variant_total if payload.variant_total > 0 else 0.0
    )
    return calculate_lift(control_rate, variant_rate)
