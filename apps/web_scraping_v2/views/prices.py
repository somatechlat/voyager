"""Price tracking API endpoints."""

from __future__ import annotations

import logging

from django.http import HttpRequest
from ninja import Query
from ninja.errors import HttpError

from ..models import PriceTrack
from ..serializers import (
    PriceNormalizeResponse,
    PriceNormalizeSchema,
    PriceTrackCreateSchema,
    PriceTrackListResponse,
    PriceTrackSchema,
)
from ..services.prices import CurrencyNormalizer

logger = logging.getLogger(__name__)


def track_price(
    request: HttpRequest,
    payload: PriceTrackCreateSchema,
) -> PriceTrackSchema:
    """Create a new price track entry.

    Args:
        request: HTTP request.
        payload: Price track creation data.

    Returns:
        The created price track.

    Raises:
        HttpError: 400 if price is invalid.
    """
    if payload.price <= 0:
        raise HttpError(400, "Price must be greater than zero")

    # Calculate discount if original price provided
    discount_pct = None
    if payload.original_price and payload.original_price > payload.price:
        discount_pct = round(
            ((payload.original_price - payload.price) / payload.original_price) * 100, 2
        )

    # Normalize currency
    normalizer = CurrencyNormalizer()
    normalized = normalizer.normalize(payload.price, payload.currency)

    track = PriceTrack.objects.create(
        tenant_id=payload.tenant_id,
        competitor_name=payload.competitor_name,
        product_name=payload.product_name,
        product_url=payload.product_url,
        price=payload.price,
        currency=payload.currency.upper(),
        original_price=payload.original_price,
        discount_pct=discount_pct,
        normalized_price=normalized["amount"],
        normalized_currency=normalized["currency"],
        exchange_rate=Decimal(str(normalized["rate"])) if normalized["rate"] else None,
        extraction_source=PriceTrack.ExtractionSource.MANUAL,
    )

    return PriceTrackSchema(
        id=track.id,
        tenant_id=track.tenant_id,
        competitor_name=track.competitor_name,
        product_name=track.product_name,
        product_url=track.product_url,
        price=track.price,
        currency=track.currency,
        original_price=track.original_price,
        discount_pct=track.discount_pct,
        normalized_price=track.normalized_price,
        normalized_currency=track.normalized_currency,
        extraction_source=track.extraction_source,
        tracked_at=track.tracked_at,
    )


def list_price_tracks(
    request: HttpRequest,
    tenant_id: str = Query("", description="Filter by tenant"),
    competitor: str = Query("", description="Filter by competitor name"),
    product: str = Query("", description="Filter by product name"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PriceTrackListResponse:
    """List price tracks with optional filtering.

    Args:
        request: HTTP request.
        tenant_id: Optional tenant filter.
        competitor: Optional competitor name filter.
        product: Optional product name filter.
        page: Page number (1-indexed).
        page_size: Items per page.

    Returns:
        Paginated price track list.
    """
    qs = PriceTrack.objects.all()

    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if competitor:
        qs = qs.filter(competitor_name__icontains=competitor)
    if product:
        qs = qs.filter(product_name__icontains=product)

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = qs.order_by("-tracked_at")[start:end]

    return PriceTrackListResponse(
        items=[
            PriceTrackSchema(
                id=t.id,
                tenant_id=t.tenant_id,
                competitor_name=t.competitor_name,
                product_name=t.product_name,
                product_url=t.product_url,
                price=t.price,
                currency=t.currency,
                original_price=t.original_price,
                discount_pct=t.discount_pct,
                normalized_price=t.normalized_price,
                normalized_currency=t.normalized_currency,
                extraction_source=t.extraction_source,
                tracked_at=t.tracked_at,
            )
            for t in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


def normalize_price(
    request: HttpRequest,
    payload: PriceNormalizeSchema,
) -> PriceNormalizeResponse:
    """Normalize a price to a target currency.

    Args:
        request: HTTP request.
        payload: Normalization data.

    Returns:
        Normalized price response.
    """
    normalizer = CurrencyNormalizer(target_currency=payload.to_currency.upper())
    result = normalizer.normalize(payload.amount, payload.from_currency.upper())

    rate = Decimal(str(result["rate"])) if result["rate"] else None

    return PriceNormalizeResponse(
        amount=result["amount"],
        currency=result["currency"],
        rate=rate,
        original=result["original"],
    )


from decimal import Decimal
