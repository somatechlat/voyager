"""Base/shared Ninja schemas for Billing."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from ninja import Schema


class TaxRateSchema(Schema):
    """Tax rate definition."""

    name: str
    rate: Decimal
