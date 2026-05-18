"""Influencer discovery and management views.

Endpoints for influencer search, vetting, outreach tracking,
and profile management.
"""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.social_media.models import InfluencerProfile
from apps.social_media.services.influencers import (
    calculate_match_score,
    estimate_rate,
    search_influencers,
    update_outreach_status,
    verify_authenticity,
)

router = Router(auth=VoyagerKeycloakBearer())


class InfluencerOut:
    """Output schema for an influencer profile."""

    id: str
    platform: str
    name: str
    avatar: str
    bio: str
    followers: int
    following: int
    engagement_rate: float
    niche: list[str]
    location: str
    authenticity_score: float
    rate_estimate: float
    content_quality_score: float
    match_score: float
    status: str
    outreach_status: str
    outreach_sent_at: str | None
    responded_at: str | None
    contact_email: str
    website: str
    created_at: str


class InfluencerSearchIn:
    """Input schema for influencer search."""

    niche: list[str] = []
    location: str = ""
    min_followers: int = 0
    max_followers: int = 0
    min_engagement: float = 0
    platforms: list[str] = []
    limit: int = 50


class OutreachIn:
    """Input schema for outreach status update."""

    status: str


class NotesIn:
    """Input schema for updating notes."""

    notes: str


@router.get("/influencers", response=list[InfluencerOut], tags=["SM Influencers"])
def list_influencers(
    request,
    tenant_id: str = "",
    platform: str = "",
    status: str = "",
    niche: str = "",
    limit: int = 50,
    offset: int = 0,
):
    """List influencer profiles with filters."""
    qs = InfluencerProfile.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if platform:
        qs = qs.filter(platform=platform)
    if status:
        qs = qs.filter(status=status)
    if niche:
        qs = qs.filter(niche__contains=[niche])
    qs = qs.order_by("-match_score")[offset : offset + limit]
    return [_influencer_to_dict(i) for i in qs]


@router.post("/influencers/search", response=list[InfluencerOut], tags=["SM Influencers"])
def search(request, payload: InfluencerSearchIn):
    """Search influencers by criteria."""
    tenant_id = getattr(request, "tenant_id", "default")
    results = search_influencers(
        tenant_id=tenant_id,
        niche=payload.niche or None,
        location=payload.location or None,
        min_followers=payload.min_followers or None,
        max_followers=payload.max_followers or None,
        min_engagement=payload.min_engagement or None,
        platforms=payload.platforms or None,
        limit=payload.limit,
    )
    return [InfluencerOut(**r) for r in results]


@router.get("/influencers/{influencer_id}", response=InfluencerOut, tags=["SM Influencers"])
def get_influencer(request, influencer_id: str):
    """Get a single influencer profile."""
    inf = get_object_or_404(InfluencerProfile, id=influencer_id)
    return _influencer_to_dict(inf)


@router.post(
    "/influencers/{influencer_id}/vet",
    response=dict,
    tags=["SM Influencers"],
)
def vet_influencer(request, influencer_id: str):
    """Run authenticity vetting on an influencer."""
    inf = get_object_or_404(InfluencerProfile, id=influencer_id)
    result = verify_authenticity(inf)
    return result


@router.post(
    "/influencers/{influencer_id}/rate",
    response=dict,
    tags=["SM Influencers"],
)
def get_rate(request, influencer_id: str):
    """Estimate collaboration rate for an influencer."""
    inf = get_object_or_404(InfluencerProfile, id=influencer_id)
    return estimate_rate(inf)


@router.post(
    "/influencers/{influencer_id}/match",
    response=dict,
    tags=["SM Influencers"],
)
def match_influencer(request, influencer_id: str):
    """Calculate match score for an influencer."""
    inf = get_object_or_404(InfluencerProfile, id=influencer_id)
    score = calculate_match_score(inf, {})
    return {"match_score": score}


@router.patch(
    "/influencers/{influencer_id}/status",
    response=InfluencerOut,
    tags=["SM Influencers"],
)
def update_status(request, influencer_id: str, status: str):
    """Update influencer pipeline status."""
    inf = get_object_or_404(InfluencerProfile, id=influencer_id)
    inf.status = status
    inf.save(update_fields=["status"])
    return _influencer_to_dict(inf)


@router.patch(
    "/influencers/{influencer_id}/outreach",
    response=InfluencerOut,
    tags=["SM Influencers"],
)
def update_outreach(request, influencer_id: str, payload: OutreachIn):
    """Update influencer outreach status."""
    inf = get_object_or_404(InfluencerProfile, id=influencer_id)
    update_outreach_status(inf, payload.status)
    return _influencer_to_dict(inf)


@router.patch(
    "/influencers/{influencer_id}/notes",
    response=InfluencerOut,
    tags=["SM Influencers"],
)
def update_notes(request, influencer_id: str, payload: NotesIn):
    """Update influencer internal notes."""
    inf = get_object_or_404(InfluencerProfile, id=influencer_id)
    inf.notes = payload.notes
    inf.save(update_fields=["notes"])
    return _influencer_to_dict(inf)


@router.get("/influencers/stats/pipeline", response=dict, tags=["SM Influencers"])
def pipeline_stats(request, tenant_id: str = ""):
    """Get influencer pipeline statistics."""
    qs = InfluencerProfile.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    return {
        "total": qs.count(),
        "by_status": {
            "discovered": qs.filter(status="discovered").count(),
            "vetting": qs.filter(status="vetting").count(),
            "approved": qs.filter(status="approved").count(),
            "rejected": qs.filter(status="rejected").count(),
            "contacted": qs.filter(status="contacted").count(),
            "negotiating": qs.filter(status="negotiating").count(),
            "contracted": qs.filter(status="contracted").count(),
            "active": qs.filter(status="active").count(),
            "completed": qs.filter(status="completed").count(),
        },
        "avg_authenticity": 0,
        "outreach_pending": qs.filter(outreach_status="not_contacted").count(),
    }


def _influencer_to_dict(i: InfluencerProfile) -> dict[str, Any]:
    """Convert InfluencerProfile to response dict."""
    return {
        "id": str(i.id),
        "platform": i.platform,
        "name": i.name,
        "avatar": i.avatar,
        "bio": i.bio,
        "followers": i.followers,
        "following": i.following,
        "engagement_rate": float(i.engagement_rate) if i.engagement_rate else 0,
        "niche": i.niche,
        "location": i.location,
        "authenticity_score": float(i.authenticity_score) if i.authenticity_score else 0,
        "rate_estimate": float(i.rate_estimate) if i.rate_estimate else 0,
        "content_quality_score": float(i.content_quality_score) if i.content_quality_score else 0,
        "match_score": float(i.match_score) if i.match_score else 0,
        "status": i.status,
        "outreach_status": i.outreach_status,
        "outreach_sent_at": i.outreach_sent_at.isoformat() if i.outreach_sent_at else None,
        "responded_at": i.responded_at.isoformat() if i.responded_at else None,
        "contact_email": i.contact_email,
        "website": i.website,
        "created_at": i.created_at.isoformat(),
    }
