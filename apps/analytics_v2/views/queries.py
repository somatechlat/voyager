"""Saved queries and SQL federation views.

Provides endpoints for managing saved queries, executing ad-hoc SQL,
and building queries via the structured query builder.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.analytics_v2.models.query import SavedQuery
from apps.analytics_v2.serializers import (
    QueryExecuteIn,
    QueryExecuteOut,
    SavedQueryCreateIn,
    SavedQueryOut,
    SavedQueryUpdateIn,
)
from apps.analytics_v2.services.trino import (
    build_query_from_builder,
    execute_query,
    validate_query,
)
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


def _tenant_from_request(request) -> str:
    """Extract tenant_id from the authenticated request."""
    return getattr(request, "tenant_id", "default")


def _user_from_request(request) -> str:
    """Extract user_id from the authenticated request."""
    user = getattr(request, "auth", None)
    if user and hasattr(user, "sub"):
        return str(user.sub)
    return "anonymous"


# ---------------------------------------------------------------------------
# Saved Query CRUD
# ---------------------------------------------------------------------------


@router.get("/saved-queries", response=list[SavedQueryOut], tags=["Queries"])
def list_saved_queries(request, public_only: bool = False) -> list[SavedQuery]:
    """List saved queries for the current tenant.

    Args:
        public_only: Filter to public queries only.
    """
    tenant_id = _tenant_from_request(request)
    qs = SavedQuery.objects.filter(tenant_id=tenant_id)
    if public_only:
        qs = qs.filter(is_public=True)
    return list(qs)


@router.get("/saved-queries/{query_id}", response=SavedQueryOut, tags=["Queries"])
def get_saved_query(request, query_id: UUID) -> SavedQuery:
    """Get a single saved query."""
    tenant_id = _tenant_from_request(request)
    return get_object_or_404(SavedQuery, id=query_id, tenant_id=tenant_id)


@router.post("/saved-queries", response=SavedQueryOut, tags=["Queries"])
def create_saved_query(request, payload: SavedQueryCreateIn) -> SavedQuery:
    """Create a new saved query."""
    tenant_id = _tenant_from_request(request)
    user_id = _user_from_request(request)

    query = SavedQuery.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        sql=payload.sql,
        query_builder=payload.query_builder,
        data_source=payload.data_source,
        is_public=payload.is_public,
        created_by=user_id,
    )
    return query


@router.patch("/saved-queries/{query_id}", response=SavedQueryOut, tags=["Queries"])
def update_saved_query(request, query_id: UUID, payload: SavedQueryUpdateIn) -> SavedQuery:
    """Update a saved query."""
    tenant_id = _tenant_from_request(request)
    query = get_object_or_404(SavedQuery, id=query_id, tenant_id=tenant_id)

    for attr in ["name", "description", "sql", "query_builder", "data_source", "is_public"]:
        val = getattr(payload, attr, None)
        if val is not None:
            setattr(query, attr, val)
    query.save()
    return query


@router.delete("/saved-queries/{query_id}", tags=["Queries"])
def delete_saved_query(request, query_id: UUID) -> dict[str, str]:
    """Delete a saved query."""
    tenant_id = _tenant_from_request(request)
    query = get_object_or_404(SavedQuery, id=query_id, tenant_id=tenant_id)
    query.delete()
    return {"status": "deleted", "id": str(query_id)}


# ---------------------------------------------------------------------------
# Query Execution
# ---------------------------------------------------------------------------


@router.post("/queries/execute", response=QueryExecuteOut, tags=["Queries"])
def execute_query_endpoint(request, payload: QueryExecuteIn) -> dict[str, Any]:
    """Execute a saved or ad-hoc query.

    Supports raw SQL, structured query builder, and saved query references.
    Routes to the appropriate data source engine.
    """
    tenant_id = _tenant_from_request(request)
    user_id = _user_from_request(request)

    # Resolve saved query
    if payload.query_id:
        sq = get_object_or_404(SavedQuery, id=payload.query_id, tenant_id=tenant_id)
        sql = sq.sql
        data_source = sq.data_source
        query_builder = sq.query_builder
    else:
        sql = payload.sql
        data_source = payload.data_source
        query_builder = payload.query_builder

    # Build from query builder if no SQL provided
    if not sql and query_builder:
        sql = build_query_from_builder(query_builder)

    if not sql:
        return {
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_time_ms": 0,
            "data_source": data_source,
            "error": "No SQL or query builder config provided",
        }

    # Validate
    validation = validate_query(sql)
    if not validation["is_valid"]:
        return {
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_time_ms": 0,
            "data_source": data_source,
            "error": f"Query validation failed: {'; '.join(validation['errors'])}",
        }

    result = execute_query(
        sql=sql,
        tenant_id=tenant_id,
        data_source=data_source,
        limit=payload.limit,
        user_id=user_id,
    )

    # Update saved query last_run stats
    if payload.query_id:
        from datetime import datetime

        sq.last_run_at = datetime.utcnow()
        sq.last_run_rows = result.get("row_count", 0)
        sq.last_run_duration_ms = result.get("execution_time_ms", 0)
        sq.save(update_fields=["last_run_at", "last_run_rows", "last_run_duration_ms"])

    return {
        "columns": result.get("columns", []),
        "rows": result.get("rows", []),
        "row_count": result.get("row_count", 0),
        "execution_time_ms": result.get("execution_time_ms", 0),
        "data_source": result.get("data_source", data_source),
    }


@router.post("/queries/validate", tags=["Queries"])
def validate_query_endpoint(request, payload: dict[str, str]) -> dict[str, Any]:
    """Validate a SQL query without executing it.

    Returns validation status, referenced tables, errors, and warnings.
    """
    sql = payload.get("sql", "")
    return validate_query(sql)


@router.post("/queries/build", tags=["Queries"])
def build_query_endpoint(request, payload: dict[str, Any]) -> dict[str, str]:
    """Build SQL from a structured query builder configuration."""
    sql = build_query_from_builder(payload)
    return {"sql": sql}


# ---------------------------------------------------------------------------
# Query catalog / data sources
# ---------------------------------------------------------------------------


@router.get("/queries/data-sources", tags=["Queries"])
def list_data_sources(request) -> dict[str, Any]:
    """List available data sources for query execution."""
    return {
        "data_sources": [
            {
                "key": "clickhouse",
                "name": "ClickHouse Analytics",
                "description": "Primary analytics data warehouse",
                "tables": [
                    "analytics_events",
                    "campaign_metrics",
                    "platform_metrics",
                    "conversion_events",
                    "funnel_events",
                    "audience_segments",
                ],
            },
            {
                "key": "postgres",
                "name": "PostgreSQL Application",
                "description": "Application metadata and configuration",
                "tables": [
                    "voyager_user",
                    "voyager_role",
                    "voyager_workspace",
                    "analytics_dashboard",
                    "analytics_widget",
                ],
            },
            {
                "key": "trino",
                "name": "Trino Federation",
                "description": "Federated queries across all sources",
                "tables": ["all_analytics", "unified_metrics"],
            },
        ]
    }
