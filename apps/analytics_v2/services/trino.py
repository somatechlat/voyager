"""SQL federation service using Trino as the query engine.

Routes queries to the appropriate data source (ClickHouse, PostgreSQL,
or Trino for federated queries), with query caching, validation, and
audit logging.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from typing import Any

logger = logging.getLogger(__name__)

# Known table mappings per data source
CLICKHOUSE_TABLES = {
    "analytics_events",
    "analytics_events_mv",
    "campaign_metrics",
    "platform_metrics",
    "audience_segments",
    "conversion_events",
    "funnel_events",
}

POSTGRES_TABLES = {
    "voyager_user",
    "voyager_role",
    "voyager_workspace",
    "voyager_permission",
    "analytics_dashboard",
    "analytics_widget",
    "analytics_report_template",
    "analytics_export_job",
}

TRINO_DEFAULT_TIMEOUT = 300  # 5 minutes
CACHE_TTL = 300  # 5 minutes


def execute_query(
    sql: str,
    tenant_id: str,
    data_source: str = "auto",
    limit: int = 1000,
    use_cache: bool = True,
    user_id: str = "",
) -> dict[str, Any]:
    """Execute a SQL query with automatic source routing.

    Parses the SQL to determine the appropriate execution engine,
    applies tenant scoping, and returns results with metadata.

    Args:
        sql: SQL query string.
        tenant_id: Tenant scope for row-level security.
        data_source: Target source (clickhouse, postgres, trino, auto).
        limit: Maximum rows to return.
        use_cache: Whether to use query result caching.
        user_id: User ID for audit logging.

    Returns:
        Dict with columns, rows, execution_time_ms, row_count, source.
    """
    start_time = time.time()
    sql = sql.strip()

    if not sql:
        return {
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_time_ms": 0,
            "data_source": data_source,
            "error": "Empty query",
        }

    # Inject tenant scoping
    sql = _inject_tenant_scope(sql, tenant_id)

    # Apply LIMIT
    if limit > 0 and not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        sql = f"{sql} LIMIT {limit}"

    # Determine data source
    if data_source == "auto":
        data_source = _route_query(sql)

    # Check cache
    if use_cache and data_source in ("clickhouse", "trino"):
        cache_key = _query_hash(sql)
        cached = _get_cached_result(cache_key)
        if cached:
            cached["from_cache"] = True
            _log_query(
                user_id, tenant_id, sql, cached.get("row_count", 0), 0, data_source, cached=True
            )
            return cached

    # Execute query
    try:
        if data_source == "clickhouse":
            result = _execute_clickhouse(sql, limit)
        elif data_source == "postgres":
            result = _execute_postgres(sql, limit)
        elif data_source == "trino":
            result = _execute_trino(sql, limit)
        else:
            result = {
                "columns": [],
                "rows": [],
                "row_count": 0,
                "execution_time_ms": 0,
                "data_source": data_source,
                "error": f"Unknown data source: {data_source}",
            }
    except Exception as exc:
        logger.error("Query execution failed on %s: %s", data_source, exc)
        result = {
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_time_ms": int((time.time() - start_time) * 1000),
            "data_source": data_source,
            "error": str(exc),
        }

    result["from_cache"] = False

    # Cache result
    if use_cache and "error" not in result and data_source in ("clickhouse", "trino"):
        _cache_result(_query_hash(sql), result)

    # Log query
    _log_query(
        user_id,
        tenant_id,
        sql,
        result.get("row_count", 0),
        result.get("execution_time_ms", 0),
        data_source,
    )

    return result


def _route_query(sql: str) -> str:
    """Route a query to the appropriate engine based on referenced tables.

    Args:
        sql: SQL query string.

    Returns:
        Data source identifier.
    """
    tables = _extract_tables(sql)

    all_in_clickhouse = all(t in CLICKHOUSE_TABLES for t in tables)
    all_in_postgres = all(t in POSTGRES_TABLES for t in tables)

    if tables and all_in_clickhouse:
        return "clickhouse"
    elif tables and all_in_postgres:
        return "postgres"
    elif tables:
        return "trino"
    # Default to ClickHouse for analytics queries
    return "clickhouse"


def _extract_tables(sql: str) -> set[str]:
    """Extract table names from a SQL query.

    Args:
        sql: SQL query string.

    Returns:
        Set of table names.
    """
    tables: set[str] = set()
    # FROM table_name
    from_matches = re.findall(r"\bfrom\s+(\w+)", sql, re.IGNORECASE)
    tables.update(from_matches)
    # JOIN table_name
    join_matches = re.findall(r"\bjoin\s+(\w+)", sql, re.IGNORECASE)
    tables.update(join_matches)
    return tables


def _inject_tenant_scope(sql: str, tenant_id: str) -> str:
    """Inject tenant_id filter into the WHERE clause.

    Args:
        sql: Original SQL query.
        tenant_id: Tenant scope.

    Returns:
        Modified SQL with tenant scoping.
    """
    if re.search(r"\btenant_id\s*[=]", sql, re.IGNORECASE):
        return sql  # Already scoped

    tenant_clause = f"tenant_id = '{tenant_id}'"
    if re.search(r"\bwhere\b", sql, re.IGNORECASE):
        sql = re.sub(r"\bwhere\b", f"WHERE {tenant_clause} AND ", sql, count=1, flags=re.IGNORECASE)
    else:
        sql = f"{sql} WHERE {tenant_clause}"

    return sql


def _execute_clickhouse(sql: str, limit: int) -> dict[str, Any]:
    """Execute query against ClickHouse.

    Args:
        sql: SQL query string.
        limit: Row limit.

    Returns:
        Query result dict.
    """
    from django.db import connections

    start = time.time()
    ch = connections.get("clickhouse")

    with ch.cursor() as cursor:
        cursor.execute(sql)
        cols = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]

    return {
        "columns": cols,
        "rows": rows,
        "row_count": len(rows),
        "execution_time_ms": int((time.time() - start) * 1000),
        "data_source": "clickhouse",
    }


def _execute_postgres(sql: str, limit: int) -> dict[str, Any]:
    """Execute query against PostgreSQL.

    Args:
        sql: SQL query string.
        limit: Row limit.

    Returns:
        Query result dict.
    """
    from django.db import connections

    start = time.time()
    pg = connections.get("default")

    with pg.cursor() as cursor:
        cursor.execute(sql)
        cols = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]

    return {
        "columns": cols,
        "rows": rows,
        "row_count": len(rows),
        "execution_time_ms": int((time.time() - start) * 1000),
        "data_source": "postgres",
    }


def _execute_trino(sql: str, limit: int) -> dict[str, Any]:
    """Execute query via Trino federation engine.

    Args:
        sql: SQL query string.
        limit: Row limit.

    Returns:
        Query result dict.
    """
    start = time.time()

    try:
        import trino

        conn = trino.dbapi.connect(
            host="localhost",
            port=8080,
            user="voyager",
            catalog="voyager",
            schema="analytics",
        )
        cur = conn.cursor()
        cur.execute(sql)
        cols = [desc[0] for desc in cur.description] if cur.description else []
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        conn.close()

        return {
            "columns": cols,
            "rows": rows,
            "row_count": len(rows),
            "execution_time_ms": int((time.time() - start) * 1000),
            "data_source": "trino",
        }
    except ImportError:
        # Fallback to ClickHouse if Trino not available
        logger.warning("Trino client not available, falling back to ClickHouse")
        return _execute_clickhouse(sql, limit)
    except Exception as exc:
        logger.error("Trino query failed: %s", exc)
        # Fallback
        return _execute_clickhouse(sql, limit)


def _query_hash(sql: str) -> str:
    """Generate a cache key from a SQL query.

    Args:
        sql: SQL query string.

    Returns:
        MD5 hex digest of the normalized query.
    """
    normalized = re.sub(r"\s+", " ", sql.strip().lower())
    return hashlib.md5(normalized.encode()).hexdigest()


def _get_cached_result(cache_key: str) -> dict[str, Any] | None:
    """Retrieve cached query result.

    Args:
        cache_key: Cache key from _query_hash().

    Returns:
        Cached result dict or None.
    """
    try:
        from django.core.cache import cache

        return cache.get(f"trino_query_{cache_key}")
    except Exception:
        return None


def _cache_result(cache_key: str, result: dict[str, Any]) -> None:
    """Cache query result with TTL.

    Args:
        cache_key: Cache key from _query_hash().
        result: Result dict to cache.
    """
    try:
        from django.core.cache import cache

        cache.set(f"trino_query_{cache_key}", result, timeout=CACHE_TTL)
    except Exception:
        logger.debug("Failed to cache Trino query result", exc_info=True)


def _log_query(
    user_id: str,
    tenant_id: str,
    sql: str,
    row_count: int,
    execution_time_ms: int,
    data_source: str,
    cached: bool = False,
) -> None:
    """Log query execution for audit purposes.

    Args:
        user_id: User who executed the query.
        tenant_id: Tenant scope.
        sql: Executed SQL.
        row_count: Rows returned.
        execution_time_ms: Query duration.
        data_source: Engine used.
        cached: Whether result was from cache.
    """
    logger.info(
        "Query audit: user=%s tenant=%s source=%s rows=%d time_ms=%d cached=%s sql=%.200s",
        user_id,
        tenant_id,
        data_source,
        row_count,
        execution_time_ms,
        cached,
        sql,
    )


def validate_query(sql: str) -> dict[str, Any]:
    """Validate a SQL query for security and syntax issues.

    Args:
        sql: SQL query string.

    Returns:
        Dict with is_valid, errors list, tables referenced, and warnings.
    """
    errors = []
    warnings_list = []

    # Check for dangerous operations
    dangerous = ["drop", "truncate", "delete", "update", "insert", "alter", "grant"]
    sql_lower = sql.lower().strip()

    if not sql:
        errors.append("Empty query")
        return {"is_valid": False, "errors": errors, "tables": set(), "warnings": warnings_list}

    # Must start with SELECT
    if not sql_lower.startswith("select"):
        errors.append("Only SELECT queries are allowed")

    for op in dangerous:
        if re.search(rf"\b{op}\b", sql_lower):
            errors.append(f"Dangerous operation detected: {op.upper()}")

    # Check for unparameterized values (basic heuristic)
    if re.search(r"=\s*'[^']*'", sql) and "tenant_id" not in sql_lower:
        warnings_list.append("Hardcoded string values detected; use parameterized queries")

    tables = _extract_tables(sql)
    if not tables:
        warnings_list.append("No tables referenced in query")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "tables": tables,
        "warnings": warnings_list,
    }


def build_query_from_builder(config: dict[str, Any]) -> str:
    """Build SQL from a structured query builder configuration.

    Args:
        config: Query builder dict with select, from, joins, where, groupBy, orderBy, limit.

    Returns:
        Generated SQL string.
    """
    selects = []
    for sel in config.get("select", []):
        metric = sel.get("metric", "*")
        agg = sel.get("aggregation", "")
        alias = sel.get("alias", "")
        if agg:
            selects.append(f"{agg}({metric}) AS {alias}" if alias else f"{agg}({metric})")
        else:
            selects.append(f"{metric} AS {alias}" if alias else metric)

    select_clause = ", ".join(selects) if selects else "*"
    from_table = config.get("from", "analytics_events")

    # Joins
    joins = []
    for join in config.get("joins", []):
        table = join.get("table", "")
        on_clause = join.get("on", "")
        join_type = join.get("type", "INNER")
        if table and on_clause:
            joins.append(f"{join_type} JOIN {table} ON {on_clause}")
    join_clause = " ".join(joins)

    # Where
    wheres = []
    for w in config.get("where", []):
        field = w.get("field", "")
        op = w.get("operator", "=")
        value = w.get("value", "")
        if field and op:
            if op == "between" and isinstance(value, list) and len(value) == 2:
                wheres.append(f"{field} BETWEEN '{value[0]}' AND '{value[1]}'")
            elif op == "in" and isinstance(value, list):
                vals = ", ".join(f"'{v}'" for v in value)
                wheres.append(f"{field} IN ({vals})")
            elif op == "contains":
                wheres.append(f"{field} LIKE '%{value}%'")
            else:
                wheres.append(f"{field} {op} '{value}'")
    where_clause = " AND ".join(wheres)

    # Group by
    groupbys = config.get("groupBy", [])
    group_clause = ", ".join(groupbys)

    # Order by
    orders = []
    for o in config.get("orderBy", []):
        field = o.get("field", "")
        direction = o.get("direction", "ASC")
        if field:
            orders.append(f"{field} {direction}")
    order_clause = ", ".join(orders)

    limit = config.get("limit", 1000)

    # Assemble
    sql = f"SELECT {select_clause} FROM {from_table}"
    if join_clause:
        sql += f" {join_clause}"
    if where_clause:
        sql += f" WHERE {where_clause}"
    if group_clause:
        sql += f" GROUP BY {group_clause}"
    if order_clause:
        sql += f" ORDER BY {order_clause}"
    if limit:
        sql += f" LIMIT {limit}"

    return sql
