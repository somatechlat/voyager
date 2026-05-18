"""PriceTrack model — price extraction and currency normalization."""

from __future__ import annotations

import uuid

from django.db import models


class PriceTrack(models.Model):
    """A tracked price point for a competitor product.

    Supports multiple extraction sources (CSS selector, JSON-LD, regex)
    with normalized currency for cross-site comparison.

    Attributes:
        id: UUID primary key.
        tenant_id: Tenant scope identifier.
        competitor_name: Name of the competitor site.
        product_name: Product or service name.
        product_url: URL where the price was found.
        price: Numeric price value.
        currency: ISO 4217 currency code (e.g., USD, EUR).
        original_price: Price before discount (if applicable).
        discount_pct: Calculated discount percentage.
        normalized_price: Price converted to target currency.
        normalized_currency: Target currency for normalization (default USD).
        exchange_rate: Rate used for normalization.
        extraction_source: Method used to extract the price.
        tracked_at: When the price was recorded.
        created_at: Record creation timestamp.
    """

    class ExtractionSource(models.TextChoices):
        CSS = "css", "CSS Selector"
        JSON_LD = "json-ld", "JSON-LD Structured Data"
        REGEX = "regex", "Regex Fallback"
        API = "api", "API Endpoint"
        MANUAL = "manual", "Manual Entry"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    competitor_name = models.CharField(max_length=255, db_index=True)
    product_name = models.CharField(max_length=500, db_index=True)
    product_url = models.URLField(max_length=2048, blank=True, default="")
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    original_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    discount_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    normalized_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    normalized_currency = models.CharField(max_length=3, default="USD")
    exchange_rate = models.DecimalField(max_digits=15, decimal_places=8, null=True, blank=True)
    extraction_source = models.CharField(
        max_length=20,
        choices=ExtractionSource.choices,
        default=ExtractionSource.CSS,
    )
    tracked_at = models.DateTimeField(auto_now_add=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ws_price_tracks"
        indexes = [
            models.Index(fields=["tenant_id", "competitor_name", "product_name"]),
            models.Index(fields=["tenant_id", "tracked_at"]),
        ]
        ordering = ["-tracked_at"]

    def __str__(self) -> str:
        return f"PriceTrack({self.product_name}, {self.price} {self.currency})"
