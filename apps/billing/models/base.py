"""Abstract base models for Billing.

Re-exports TimeStampedModel from apps.core.models so all billing models
use the canonical base class.
"""

from __future__ import annotations

from apps.core.models import TimeStampedModel  # noqa: F401
