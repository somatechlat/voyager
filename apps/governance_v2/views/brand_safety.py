"""Brand safety API endpoint handlers."""

from __future__ import annotations

from django.http import HttpRequest

from apps.governance_v2.serializers import (
    ContentScanRequest,
    ContentScanResponse,
)
from apps.governance_v2.services import BrandSafetyService


def scan_content(
    request: HttpRequest,
    payload: ContentScanRequest,
) -> ContentScanResponse:
    """Scan content for brand safety violations.

    Checks the provided text against profanity filters, sensitive
    topic detectors, competitor lists, and industry-specific rules.

    Args:
        request: HTTP request.
        payload: Content scan request body.

    Returns:
        Content scan results with violations and recommended action.
    """
    result = BrandSafetyService.scan_content(
        content=payload.content,
        tenant_id=payload.tenant_id,
        industry=payload.industry,
        content_type=payload.content_type,
        metadata=payload.metadata,
    )

    violations = [
        {
            "type": v["type"],
            "severity": v["severity"],
            "message": v["message"],
            "details": v.get("details", {}),
        }
        for v in result["violations"]
    ]

    return ContentScanResponse(
        passed=result["passed"],
        action=result["action"],
        violations=violations,
        scan_timestamp=result["scan_timestamp"],
    )
