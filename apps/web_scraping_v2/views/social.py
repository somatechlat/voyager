"""Social mention API endpoints."""

from __future__ import annotations

import hashlib
import logging
from datetime import timedelta

from django.http import HttpRequest
from django.utils import timezone
from ninja import Query
from ninja.errors import HttpError

from ..models import SocialMention
from ..serializers import (
    ShareOfVoiceResponse,
    ShareOfVoiceSchema,
    SocialMentionCreateSchema,
    SocialMentionListResponse,
    SocialMentionSchema,
)

logger = logging.getLogger(__name__)


def _generate_fingerprint(mention: SocialMentionCreateSchema) -> str:
    """Generate a content fingerprint for deduplication.

    Args:
        mention: The mention data.

    Returns:
        SHA-256 hex digest fingerprint.
    """
    normalized = mention.text.lower().strip()[:500]
    raw = f"{normalized}|{mention.author}|{mention.platform}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _check_cross_post(
    mention: SocialMentionCreateSchema,
    fingerprint: str,
) -> SocialMention | None:
    """Check if a mention is a cross-post of existing content.

    Args:
        mention: The new mention data.
        fingerprint: Content fingerprint.

    Returns:
        Existing mention if cross-post detected, None otherwise.
    """
    text_normalized = mention.text.lower().strip()[:500]
    text_hash = hashlib.sha256(text_normalized.encode("utf-8")).hexdigest()

    # Look for same content on different platform within 24h
    recent = SocialMention.objects.filter(
        brand=mention.brand,
        collected_at__gte=timezone.now() - timedelta(hours=24),
    )

    for existing in recent:
        existing_text_hash = hashlib.sha256(
            existing.text.lower().strip()[:500].encode("utf-8")
        ).hexdigest()
        if existing_text_hash == text_hash and existing.platform != mention.platform:
            return existing

    return None


def collect_mention(
    request: HttpRequest,
    payload: SocialMentionCreateSchema,
) -> SocialMentionSchema:
    """Collect a social mention with deduplication.

    Args:
        request: HTTP request.
        payload: Social mention data.

    Returns:
        The created or updated social mention.

    Raises:
        HttpError: 400 if text or brand is missing.
    """
    if not payload.text or not payload.text.strip():
        raise HttpError(400, "Text is required")
    if not payload.brand or not payload.brand.strip():
        raise HttpError(400, "Brand is required")

    fingerprint = _generate_fingerprint(payload)

    # Check for exact duplicate
    existing = SocialMention.objects.filter(fingerprint=fingerprint).first()
    if existing:
        return SocialMentionSchema(
            id=existing.id,
            tenant_id=existing.tenant_id,
            brand=existing.brand,
            platform=existing.platform,
            author=existing.author,
            text=existing.text,
            url=existing.url,
            fingerprint=existing.fingerprint,
            sentiment=existing.sentiment,
            sentiment_score=existing.sentiment_score,
            engagement=existing.engagement,
            cross_platforms=existing.cross_platforms,
            published_at=existing.published_at,
            collected_at=existing.collected_at,
        )

    # Check for cross-post
    cross_post = _check_cross_post(payload, fingerprint)
    if cross_post:
        platforms: list[str] = (
            list(cross_post.cross_platforms) if cross_post.cross_platforms else []
        )
        if payload.platform not in platforms:
            platforms.append(payload.platform)
        cross_post.cross_platforms = platforms
        cross_post.save(update_fields=["cross_platforms"])
        return SocialMentionSchema(
            id=cross_post.id,
            tenant_id=cross_post.tenant_id,
            brand=cross_post.brand,
            platform=cross_post.platform,
            author=cross_post.author,
            text=cross_post.text,
            url=cross_post.url,
            fingerprint=cross_post.fingerprint,
            sentiment=cross_post.sentiment,
            sentiment_score=cross_post.sentiment_score,
            engagement=cross_post.engagement,
            cross_platforms=cross_post.cross_platforms,
            published_at=cross_post.published_at,
            collected_at=cross_post.collected_at,
        )

    mention = SocialMention.objects.create(
        tenant_id=payload.tenant_id,
        brand=payload.brand,
        platform=payload.platform,
        author=payload.author,
        text=payload.text,
        url=payload.url,
        fingerprint=fingerprint,
        engagement=payload.engagement,
        published_at=payload.published_at,
    )

    return SocialMentionSchema(
        id=mention.id,
        tenant_id=mention.tenant_id,
        brand=mention.brand,
        platform=mention.platform,
        author=mention.author,
        text=mention.text,
        url=mention.url,
        fingerprint=mention.fingerprint,
        sentiment=mention.sentiment,
        sentiment_score=mention.sentiment_score,
        engagement=mention.engagement,
        cross_platforms=mention.cross_platforms,
        published_at=mention.published_at,
        collected_at=mention.collected_at,
    )


def list_social_mentions(
    request: HttpRequest,
    tenant_id: str = Query("", description="Filter by tenant"),
    brand: str = Query("", description="Filter by brand"),
    platform: str = Query("", description="Filter by platform"),
    sentiment: str = Query("", description="Filter by sentiment"),
    days: int = Query(30, ge=1, le=365),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> SocialMentionListResponse:
    """List social mentions with optional filtering.

    Args:
        request: HTTP request.
        tenant_id: Optional tenant filter.
        brand: Optional brand filter.
        platform: Optional platform filter.
        sentiment: Optional sentiment filter.
        days: Number of days to look back.
        page: Page number (1-indexed).
        page_size: Items per page.

    Returns:
        Paginated social mention list.
    """
    qs = SocialMention.objects.filter(collected_at__gte=timezone.now() - timedelta(days=days))

    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if brand:
        qs = qs.filter(brand__icontains=brand)
    if platform:
        qs = qs.filter(platform=platform)
    if sentiment:
        qs = qs.filter(sentiment=sentiment)

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = qs.order_by("-collected_at")[start:end]

    return SocialMentionListResponse(
        items=[
            SocialMentionSchema(
                id=m.id,
                tenant_id=m.tenant_id,
                brand=m.brand,
                platform=m.platform,
                author=m.author,
                text=m.text,
                url=m.url,
                fingerprint=m.fingerprint,
                sentiment=m.sentiment,
                sentiment_score=m.sentiment_score,
                engagement=m.engagement,
                cross_platforms=m.cross_platforms,
                published_at=m.published_at,
                collected_at=m.collected_at,
            )
            for m in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


def share_of_voice(
    request: HttpRequest,
    payload: ShareOfVoiceSchema,
) -> ShareOfVoiceResponse:
    """Calculate share of voice for a brand against competitors.

    Args:
        request: HTTP request.
        payload: Share of voice parameters.

    Returns:
        Share of voice breakdown.
    """
    since = timezone.now() - timedelta(days=payload.days)

    brand_count = (
        SocialMention.objects.filter(
            brand__iexact=payload.brand,
            collected_at__gte=since,
        ).count()
        if payload.brand
        else 0
    )

    competitor_results: list[dict[str, Any]] = []
    total_mentions = brand_count

    for comp in payload.competitors:
        comp_count = SocialMention.objects.filter(
            brand__iexact=comp,
            collected_at__gte=since,
        ).count()
        total_mentions += comp_count
        competitor_results.append(
            {
                "brand": comp,
                "mentions": comp_count,
                "sov": 0.0,
            }
        )

    brand_sov = 0.0
    if total_mentions > 0:
        brand_sov = round((brand_count / total_mentions) * 100, 2)
        for comp in competitor_results:
            comp["sov"] = round((comp["mentions"] / total_mentions) * 100, 2)

    return ShareOfVoiceResponse(
        brand={"mentions": brand_count, "sov": brand_sov},
        competitors=competitor_results,
        total_mentions=total_mentions,
    )
