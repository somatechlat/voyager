"""Abstract base models for Publishing.

Provides UUIDModel, TimeStampedModel, and TenantModel base classes
that match the Voyager spec for consistent primary keys, timestamps,
and multi-tenancy across all publishing models.
"""

from __future__ import annotations

import uuid

from django.db import models


class UUIDModel(models.Model):
    """Abstract base model using UUID primary keys."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Globally unique identifier (UUID v4)",
    )

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """Abstract base model with automatic created / updated timestamps."""

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when the record was created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
        help_text="Timestamp when the record was last updated",
    )

    class Meta:
        abstract = True


class TenantModel(models.Model):
    """Abstract base model for tenant-scoped records."""

    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )

    class Meta:
        abstract = True
