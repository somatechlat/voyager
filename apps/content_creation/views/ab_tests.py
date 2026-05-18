"""A/B Testing endpoints.

GET  /api/v1/content/ab-tests           — list A/B tests
POST /api/v1/content/ab-tests           — create A/B test
GET  /api/v1/content/ab-tests/{id}      — get A/B test
PUT  /api/v1/content/ab-tests/{id}      — update A/B test
POST /api/v1/content/ab-tests/{id}/winner  — calculate winner
"""

from __future__ import annotations

import logging
from typing import Any, List
from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.content_creation.models import ABTest
from apps.content_creation.serializers import ABTestIn, ABTestOut, WinnerOut
from apps.content_creation.services.ab_testing import calculate_winner, create_test
from apps.core.middleware import get_tenant_id

logger = logging.getLogger(__name__)

router = Router(tags=["A/B Testing"])


@router.get("/ab-tests", response=List[ABTestOut])
def list_ab_tests(request) -> list[ABTest]:
    """List all A/B tests for the current tenant."""
    tenant_id = get_tenant_id(request)
    return list(ABTest.objects.filter(tenant_id=tenant_id).order_by("-created_at"))


@router.post("/ab-tests", response=ABTestOut)
def create_ab_test(request, payload: ABTestIn) -> ABTest:
    """Create a new A/B test with variants.

    Validates the variant structure and persists the test configuration.
    The test starts in 'draft' status until explicitly started.
    """
    tenant_id = get_tenant_id(request)

    validation = create_test(
        name=payload.name,
        content_generation_id=str(payload.content_generation_id),
        variants=payload.variants,
        sample_size=payload.sample_size,
        winner_criteria=payload.winner_criteria,
        start_date=payload.start_date.isoformat() if payload.start_date else None,
        end_date=payload.end_date.isoformat() if payload.end_date else None,
        tenant_id=tenant_id,
    )

    if not validation.get("valid"):
        return {
            "id": UUID(int=0),
            "name": payload.name,
            "content_generation_id": payload.content_generation_id,
            "variants": [],
            "status": "draft",
            "winner_criteria": payload.winner_criteria,
            "results": {"error": validation.get("error", "Invalid test")},
            "tenant_id": tenant_id,
            "created_at": None,
        }  # type: ignore[return-value]

    test = ABTest.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        content_generation_id=payload.content_generation_id,
        variants=payload.variants,
        sample_size=payload.sample_size,
        winner_criteria=payload.winner_criteria,
    )
    logger.info("Created A/B test id=%s tenant=%s variants=%s", test.id, tenant_id, len(payload.variants))
    return test


@router.get("/ab-tests/{test_id}", response=ABTestOut)
def get_ab_test(request, test_id: UUID) -> ABTest:
    """Retrieve an A/B test by ID."""
    tenant_id = get_tenant_id(request)
    return get_object_or_404(ABTest, id=test_id, tenant_id=tenant_id)


@router.put("/ab-tests/{test_id}", response=ABTestOut)
def update_ab_test(request, test_id: UUID, payload: ABTestIn) -> ABTest:
    """Update an A/B test."""
    tenant_id = get_tenant_id(request)
    test = get_object_or_404(ABTest, id=test_id, tenant_id=tenant_id)
    test.name = payload.name
    test.variants = payload.variants
    test.sample_size = payload.sample_size
    test.winner_criteria = payload.winner_criteria
    test.save()
    logger.info("Updated A/B test id=%s tenant=%s", test.id, tenant_id)
    return test


@router.post("/ab-tests/{test_id}/winner", response=WinnerOut)
def get_winner(request, test_id: UUID) -> dict[str, Any]:
    """Calculate the winning variant for an A/B test.

    Runs chi-squared statistical significance tests between all
    variant pairs and returns the winner if significance is reached
    (p < 0.05).
    """
    tenant_id = get_tenant_id(request)
    test = get_object_or_404(ABTest, id=test_id, tenant_id=tenant_id)

    variants = test.variants
    if not variants:
        return {
            "winner": None,
            "confidence": 0.0,
            "significant": False,
            "message": "No variants found for this test",
            "p_value": 1.0,
        }

    result = calculate_winner(variants)
    return {
        "winner": result.get("winner"),
        "confidence": result.get("confidence", 0.0),
        "significant": result.get("significant", False),
        "message": result.get("message", ""),
        "p_value": result.get("p_value", 1.0),
    }


@router.delete("/ab-tests/{test_id}")
def delete_ab_test(request, test_id: UUID) -> dict[str, Any]:
    """Delete an A/B test."""
    tenant_id = get_tenant_id(request)
    test = get_object_or_404(ABTest, id=test_id, tenant_id=tenant_id)
    test.delete()
    logger.info("Deleted A/B test id=%s tenant=%s", test_id, tenant_id)
    return {"deleted": True, "id": str(test_id)}
