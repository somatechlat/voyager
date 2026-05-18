"""Abstract base models for Billing.

Provides TimestampedModel mixin for consistent created/updated
fields across all billing models.
"""

from __future__ import annotations

from django.db import models


class TimestampedModel(models.Model):
    """Abstract base with automatic created / updated timestamps."""

    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="When the record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, db_index=True, help_text="When the record was last updated"
    )

    class Meta:
        abstract = True
