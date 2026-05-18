"""Abstract base models for Content Creation.

Provides UUIDModel, TimeStampedModel, and TenantModel base classes
that match the Voyager spec for consistent primary keys, timestamps,
and multi-tenancy across all content models.
"""

from __future__ import annotations

import uuid

from django.db import models


class UUIDModel(models.Model):
    """Abstract base model using UUID primary keys.

    All content models inherit from this for globally unique identifiers
    that do not expose sequential allocation patterns.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Globally unique identifier (UUID v4)",
    )

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """Abstract base model with automatic created / updated timestamps.

    Provides ``created_at`` and ``updated_at`` fields that are maintained
    automatically by Django.  Both fields are indexed for efficient
    time-range queries.
    """

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
    """Abstract base model for tenant-scoped records.

    Uses a ``CharField`` for tenant_id (matching the existing RBAC pattern)
    rather than a FK so that tenant isolation is lightweight and does not
    require a separate tenants table.
    """

    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )

    class Meta:
        abstract = True
