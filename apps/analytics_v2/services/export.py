"""Data export service — streaming exports for large datasets (100K+ rows).

Handles CSV, JSON, Excel, and NDJSON exports with streaming, progress
tracking, and chunked processing for datasets exceeding 100,000 rows.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime
from typing import Any

from apps.analytics_v2.services.dashboards import compute_date_range

logger = logging.getLogger(__name__)

CHUNK_SIZE = 10000  # Rows per chunk for streaming
LARGE_DATASET_THRESHOLD = 100000


def create_export_job(
    name: str,
    description: str,
    query_config: dict[str, Any],
    export_format: str,
    columns: list[str],
    tenant_id: str,
    created_by: str,
) -> Any:
    """Create an export job record.

    Args:
        name: Export job name.
        description: Optional description.
        query_config: Query/filters configuration.
        export_format: Output format.
        columns: Columns to export.
        tenant_id: Tenant scope.
        created_by: User ID.

    Returns:
        ExportJob instance.
    """
    from apps.analytics_v2.models.export import ExportJob

    job = ExportJob.objects.create(
        tenant_id=tenant_id,
        name=name,
        description=description,
        query=query_config,
        format=export_format,
        columns=columns,
        created_by=created_by,
        status="queued",
    )
    return job


def process_export_job(job: Any) -> dict[str, Any]:
    """Process an export job: execute query, format output, update status.

    Args:
        job: ExportJob instance.

    Returns:
        Dict with status, file info, and row count.
    """
    from django.db import connections

    job.status = "running"
    job.started_at = datetime.utcnow()
    job.save(update_fields=["status", "started_at"])

    try:
        query_config = job.query
        date_range = query_config.get("date_range", {})
        start_dt, end_dt = compute_date_range(
            date_range.get("preset"),
            date_range.get("start"),
            date_range.get("end"),
        )
        filters = query_config.get("filters", {})
        source = query_config.get("source", "analytics_events")
        tenant_id = job.tenant_id

        if job.format == "csv":
            result = _stream_csv_export(job, source, start_dt, end_dt, filters, tenant_id)
        elif job.format == "json":
            result = _stream_json_export(job, source, start_dt, end_dt, filters, tenant_id)
        elif job.format == "ndjson":
            result = _stream_ndjson_export(job, source, start_dt, end_dt, filters, tenant_id)
        elif job.format == "excel":
            result = _stream_excel_export(job, source, start_dt, end_dt, filters, tenant_id)
        else:
            raise ValueError(f"Unsupported export format: {job.format}")

        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.row_count = result.get("row_count", 0)
        job.file_path = result.get("file_path", "")
        job.file_size_bytes = result.get("file_size_bytes", 0)
        job.progress_percent = 100
        job.save(update_fields=["status", "completed_at", "row_count", "file_path", "file_size_bytes", "progress_percent"])

        return {
            "status": "completed",
            "job_id": str(job.id),
            "row_count": job.row_count,
            "file_path": job.file_path,
            "file_size_bytes": job.file_size_bytes,
        }

    except Exception as exc:
        logger.error("Export job %s failed: %s", job.id, exc)
        job.status = "failed"
        job.error_message = str(exc)
        job.completed_at = datetime.utcnow()
        job.save(update_fields=["status", "error_message", "completed_at"])
        return {
            "status": "failed",
            "job_id": str(job.id),
            "error": str(exc),
        }


def _stream_csv_export(
    job: Any,
    source: str,
    start_dt: datetime,
    end_dt: datetime,
    filters: dict[str, Any],
    tenant_id: str,
) -> dict[str, Any]:
    """Stream data to CSV file with chunked reading.

    Args:
        job: ExportJob instance.
        source: Data source table.
        start_dt: Start datetime.
        end_dt: End datetime.
        filters: Query filters.
        tenant_id: Tenant scope.

    Returns:
        Dict with row_count, file_path, file_size_bytes.
    """
    import tempfile

    columns = job.columns if job.columns else []
    file_path = f"/tmp/export_{job.id}.csv"

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if columns:
            writer.writerow(columns)
        else:
            writer.writerow(["data"])

        row_count = 0
        offset = 0
        while True:
            chunk = _fetch_chunk(source, start_dt, end_dt, filters, tenant_id, columns, offset, CHUNK_SIZE)
            if not chunk:
                break
            for row in chunk:
                writer.writerow([row.get(c, "") for c in columns] if columns else [str(row)])
            row_count += len(chunk)
            offset += len(chunk)
            job.progress_percent = min(99, int(offset / max(offset, 1) * 100))
            job.save(update_fields=["progress_percent"])

            if len(chunk) < CHUNK_SIZE:
                break

    file_size = __import__("os").path.getsize(file_path)
    return {"row_count": row_count, "file_path": file_path, "file_size_bytes": file_size}


def _stream_json_export(
    job: Any,
    source: str,
    start_dt: datetime,
    end_dt: datetime,
    filters: dict[str, Any],
    tenant_id: str,
) -> dict[str, Any]:
    """Stream data to JSON file.

    Args:
        job: ExportJob instance.
        source: Data source table.
        start_dt: Start datetime.
        end_dt: End datetime.
        filters: Query filters.
        tenant_id: Tenant scope.

    Returns:
        Dict with row_count, file_path, file_size_bytes.
    """
    file_path = f"/tmp/export_{job.id}.json"
    columns = job.columns if job.columns else []

    with open(file_path, "w", encoding="utf-8") as f:
        f.write('{"data":[')
        row_count = 0
        offset = 0
        first = True

        while True:
            chunk = _fetch_chunk(source, start_dt, end_dt, filters, tenant_id, columns, offset, CHUNK_SIZE)
            if not chunk:
                break
            for row in chunk:
                if not first:
                    f.write(",")
                first = False
                f.write(json.dumps(row, default=str))
                row_count += 1
            offset += len(chunk)
            job.progress_percent = min(99, int(offset / max(offset, 1) * 100))
            job.save(update_fields=["progress_percent"])
            if len(chunk) < CHUNK_SIZE:
                break

        f.write(f'],"total":{row_count},"generated_at":"{datetime.utcnow().isoformat()}"}}')

    file_size = __import__("os").path.getsize(file_path)
    return {"row_count": row_count, "file_path": file_path, "file_size_bytes": file_size}


def _stream_ndjson_export(
    job: Any,
    source: str,
    start_dt: datetime,
    end_dt: datetime,
    filters: dict[str, Any],
    tenant_id: str,
) -> dict[str, Any]:
    """Stream data to newline-delimited JSON file.

    Args:
        job: ExportJob instance.
        source: Data source table.
        start_dt: Start datetime.
        end_dt: End datetime.
        filters: Query filters.
        tenant_id: Tenant scope.

    Returns:
        Dict with row_count, file_path, file_size_bytes.
    """
    file_path = f"/tmp/export_{job.id}.ndjson"
    columns = job.columns if job.columns else []

    with open(file_path, "w", encoding="utf-8") as f:
        row_count = 0
        offset = 0
        while True:
            chunk = _fetch_chunk(source, start_dt, end_dt, filters, tenant_id, columns, offset, CHUNK_SIZE)
            if not chunk:
                break
            for row in chunk:
                f.write(json.dumps(row, default=str) + "\n")
                row_count += 1
            offset += len(chunk)
            job.progress_percent = min(99, int(offset / max(offset, 1) * 100))
            job.save(update_fields=["progress_percent"])
            if len(chunk) < CHUNK_SIZE:
                break

    file_size = __import__("os").path.getsize(file_path)
    return {"row_count": row_count, "file_path": file_path, "file_size_bytes": file_size}


def _stream_excel_export(
    job: Any,
    source: str,
    start_dt: datetime,
    end_dt: datetime,
    filters: dict[str, Any],
    tenant_id: str,
) -> dict[str, Any]:
    """Stream data to Excel file using openpyxl.

    Args:
        job: ExportJob instance.
        source: Data source table.
        start_dt: Start datetime.
        end_dt: End datetime.
        filters: Query filters.
        tenant_id: Tenant scope.

    Returns:
        Dict with row_count, file_path, file_size_bytes.
    """
    try:
        import openpyxl
    except ImportError:
        logger.warning("openpyxl not available, falling back to CSV")
        return _stream_csv_export(job, source, start_dt, end_dt, filters, tenant_id)

    file_path = f"/tmp/export_{job.id}.xlsx"
    columns = job.columns if job.columns else []

    wb = openpyxl.Workbook(write_only=True)
    ws = wb.create_sheet(title="Export")

    if columns:
        ws.append(columns)

    row_count = 0
    offset = 0
    while True:
        chunk = _fetch_chunk(source, start_dt, end_dt, filters, tenant_id, columns, offset, CHUNK_SIZE)
        if not chunk:
            break
        for row in chunk:
            ws.append([row.get(c, "") for c in columns] if columns else list(row.values()))
            row_count += 1
        offset += len(chunk)
        job.progress_percent = min(99, int(offset / max(offset, 1) * 100))
        job.save(update_fields=["progress_percent"])
        if len(chunk) < CHUNK_SIZE:
            break

    wb.save(file_path)
    file_size = __import__("os").path.getsize(file_path)
    return {"row_count": row_count, "file_path": file_path, "file_size_bytes": file_size}


def _fetch_chunk(
    source: str,
    start: datetime,
    end: datetime,
    filters: dict[str, Any],
    tenant_id: str,
    columns: list[str],
    offset: int,
    limit: int,
) -> list[dict[str, Any]]:
    """Fetch a chunk of rows from ClickHouse.

    Args:
        source: Data source table.
        start: Start datetime.
        end: End datetime.
        filters: Query filters.
        tenant_id: Tenant scope.
        columns: Columns to select.
        offset: Row offset.
        limit: Rows per chunk.

    Returns:
        List of row dicts.
    """
    try:
        from django.db import connections

        ch = connections.get("clickhouse")
        where = f"tenant_id = '{tenant_id}' AND event_date BETWEEN '{start.date()}' AND '{end.date()}'"
        platform = filters.get("platform", "")
        if platform:
            where += f" AND platform = '{platform}'"

        col_select = ", ".join(columns) if columns else "*"
        sql = f"""
            SELECT {col_select}
            FROM {source}
            WHERE {where}
            LIMIT {limit}
            OFFSET {offset}
        """
        with ch.cursor() as cursor:
            cursor.execute(sql)
            if columns:
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
            else:
                cols = [desc[0] for desc in cursor.description]
                return [dict(zip(cols, row)) for row in cursor.fetchall()]
    except Exception:
        return []


def stream_export_response(
    job: Any,
) -> Any:
    """Generate a streaming HTTP response for an export job.

    Args:
        job: Completed ExportJob instance.

    Returns:
        StreamingHttpResponse with the file content.
    """
    from django.http import StreamingHttpResponse

    content_types = {
        "csv": "text/csv; charset=utf-8",
        "json": "application/json",
        "ndjson": "application/x-ndjson",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    ext = {"csv": "csv", "json": "json", "ndjson": "ndjson", "excel": "xlsx"}.get(job.format, job.format)

    def _file_iterator():
        with open(job.file_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    response = StreamingHttpResponse(
        _file_iterator(),
        content_type=content_types.get(job.format, "application/octet-stream"),
    )
    response["Content-Disposition"] = f'attachment; filename="export_{job.id}.{ext}"'
    response["Content-Length"] = str(job.file_size_bytes)
    return response
