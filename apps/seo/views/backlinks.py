"""Backlink analysis views.

API endpoints for backlink profile analysis, toxic link detection,
and anchor text distribution.
"""

from __future__ import annotations

import logging
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.seo.models.backlink import Backlink
from apps.seo.serializers import BacklinkProfileResponse, BacklinkResponse
from apps.seo.services.backlinks import analyze_backlink_profile, detect_toxic_links

logger = logging.getLogger(__name__)

router = Router(auth=VoyagerKeycloakBearer())


def _bl_to_schema(bl: Backlink) -> BacklinkResponse:
    """Convert Backlink model to response schema."""
    return BacklinkResponse(
        id=str(bl.id),
        sourceUrl=bl.source_url,
        targetUrl=bl.target_url,
        anchorText=bl.anchor_text or "",
        referringDomain=bl.referring_domain or "",
        domainAuthority=float(bl.domain_authority) if bl.domain_authority else None,
        pageAuthority=float(bl.page_authority) if bl.page_authority else None,
        spamScore=float(bl.spam_score) if bl.spam_score else None,
        isToxic=bl.is_toxic,
        toxicityScore=float(bl.toxicity_score) if bl.toxicity_score else 0.0,
        toxicityReasons=bl.toxicity_reasons_json or [],
        recommendedAction=bl.recommended_action,
        linkType=bl.link_type,
        status=bl.status,
        firstSeen=bl.first_seen,
        lastSeen=bl.last_seen,
        createdAt=bl.created_at,
    )


@router.get("/backlinks", response=list[BacklinkResponse], tags=["SEO Backlinks"])
def list_backlinks(
    request,
    limit: int = 100,
    target_url: str = "",
    is_toxic: bool | None = None,
) -> list[BacklinkResponse]:
    """List backlinks for the tenant.

    Query parameters:
        limit: Maximum results.
        target_url: Filter by target URL.
        is_toxic: Filter by toxicity status.
    """
    tenant_id = getattr(request, "tenant_id", "default")
    qs = Backlink.objects.filter(tenant_id=tenant_id)
    if target_url:
        qs = qs.filter(target_url=target_url)
    if is_toxic is not None:
        qs = qs.filter(is_toxic=is_toxic)
    return [_bl_to_schema(bl) for bl in qs[:limit]]


@router.get("/backlinks/{backlink_id}", response=BacklinkResponse, tags=["SEO Backlinks"])
def get_backlink(request, backlink_id: str) -> BacklinkResponse:
    """Get a single backlink by ID."""
    tenant_id = getattr(request, "tenant_id", "default")
    bl = get_object_or_404(Backlink, id=backlink_id, tenant_id=tenant_id)
    return _bl_to_schema(bl)


@router.post("/backlinks/analyze", response=BacklinkProfileResponse, tags=["SEO Backlinks"])
def analyze_backlinks(request, target_url: str = "") -> dict[str, Any]:
    """Analyze backlink profile with toxicity detection.

    Runs the full backlink analysis including toxic link detection,
    anchor text distribution, and referring domain breakdown.
    """
    tenant_id = getattr(request, "tenant_id", "default")
    return analyze_backlink_profile(tenant_id=tenant_id, target_url=target_url or None)


@router.post("/backlinks/detect-toxic", tags=["SEO Backlinks"])
def run_toxic_detection(request) -> dict[str, Any]:
    """Run toxic link detection on all tenant backlinks."""
    tenant_id = getattr(request, "tenant_id", "default")
    backlinks = list(Backlink.objects.filter(tenant_id=tenant_id))
    toxic = detect_toxic_links(backlinks)
    return {
        "status": "ok",
        "total_analyzed": len(backlinks),
        "toxic_found": len(toxic),
        "toxic_percentage": round(len(toxic) / len(backlinks) * 100, 2) if backlinks else 0,
    }


@router.get("/backlinks/profile/summary", tags=["SEO Backlinks"])
def get_profile_summary(request) -> dict[str, Any]:
    """Get a quick summary of the backlink profile."""
    tenant_id = getattr(request, "tenant_id", "default")
    total = Backlink.objects.filter(tenant_id=tenant_id).count()
    toxic = Backlink.objects.filter(tenant_id=tenant_id, is_toxic=True).count()
    domains = (
        Backlink.objects.filter(tenant_id=tenant_id).values("referring_domain").distinct().count()
    )
    return {
        "total_backlinks": total,
        "referring_domains": domains,
        "toxic_count": toxic,
        "toxic_percentage": round(toxic / total * 100, 2) if total else 0,
    }
