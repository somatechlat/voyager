"""Saved query model for SQL federation and reusable analytics queries."""

from __future__ import annotations

import uuid

from django.db import models

from apps.rbac.models import TenantScopedMixin


class SavedQuery(TenantScopedMixin, models.Model):
    """A user-saved SQL or structured query for reuse and sharing.

    Attributes:
        id: UUID primary key.
        tenant_id: Tenant scope identifier.
        name: Human-readable query name.
        description: Optional query description.
        sql: SQL query text (may contain Trino federation syntax).
        query_builder: JSON structured query (alternative to raw SQL).
        data_source: Primary data source identifier.
        is_public: Whether the query is shared with the team.
        last_run_at: When the query was last executed.
        last_run_rows: Row count from the last execution.
        last_run_duration_ms: Query execution time in milliseconds.
        created_by: User ID of the creator.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sql = models.TextField(blank=True, help_text="Raw SQL or Trino federated query")
    query_builder = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured query builder config (alternative to SQL)",
    )
    data_source = models.CharField(
        max_length=64,
        default="clickhouse",
        help_text="Primary data source: clickhouse, postgres, trino",
    )
    is_public = models.BooleanField(default=False)
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_run_rows = models.PositiveIntegerField(default=0)
    last_run_duration_ms = models.PositiveIntegerField(default=0)
    created_by = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = "analytics_saved_query"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["tenant_id", "is_public"]),
            models.Index(fields=["tenant_id", "-updated_at"]),
            models.Index(fields=["tenant_id", "data_source"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="%(app_label)s_sq_tenant_name_uniq",
            ),
        ]

    def __str__(self) -> str:
        return self.name
