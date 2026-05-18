"""Base/shared Ninja schemas for Billing."""

from __future__ import annotations

from decimal import Decimal

from ninja import Schema


class TaxRateSchema(Schema):
    """Tax rate definition."""

    name: str
    rate: Decimal
