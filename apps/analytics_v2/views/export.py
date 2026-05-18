"""Data export views for large dataset streaming.

Provides endpoints for creating, monitoring, and downloading export jobs
with support for CSV, JSON, Excel, and NDJSON formats.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.analytics_v2.models.export import ExportJob
from apps.analytics_v2.serializers import ExportCreateIn, ExportOut
from apps.analytics_v2.services.export import (
    create_export_job,
    process_export_job,
    stream_export_response,
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
# Export Job CRUD
# ---------------------------------------------------------------------------


@router.get("/exports", response=list[ExportOut], tags=["Exports"])
def list_export_jobs(request, status: str = "") -> list[ExportJob]:
    """List export jobs for the current tenant.

    Args:
        status: Optional status filter.
    """
    tenant_id = _tenant_from_request(request)
    qs = ExportJob.objects.filter(tenant_id=tenant_id)
    if status:
        qs = qs.filter(status=status)
    return list(qs)


@router.get("/exports/{job_id}", response=ExportOut, tags=["Exports"])
def get_export_job(request, job_id: UUID) -> ExportJob:
    """Get a single export job with its current status."""
    tenant_id = _tenant_from_request(request)
    return get_object_or_404(ExportJob, id=job_id, tenant_id=tenant_id)


@router.post("/exports", response=ExportOut, tags=["Exports"])
def create_export(request, payload: ExportCreateIn) -> ExportJob:
    """Create a new export job.

    The job is created in 'queued' status. Trigger processing via
    the /exports/{job_id}/process endpoint or a Celery task.
    """
    tenant_id = _tenant_from_request(request)
    user_id = _user_from_request(request)

    job = create_export_job(
        name=payload.name,
        description=payload.description,
        query_config=payload.query,
        export_format=payload.format,
        columns=payload.columns,
        tenant_id=tenant_id,
        created_by=user_id,
    )
    return job


@router.post("/exports/{job_id}/process", tags=["Exports"])
def process_export(request, job_id: UUID) -> dict[str, Any]:
    """Start processing a queued export job.

    Executes the query, formats the output, and updates the job status.
    """
    tenant_id = _tenant_from_request(request)
    job = get_object_or_404(ExportJob, id=job_id, tenant_id=tenant_id)

    if job.status not in ("queued", "failed"):
        return {
            "status": "skipped",
            "job_id": str(job_id),
            "message": f"Job is already {job.status}",
        }

    result = process_export_job(job)
    return result


@router.get("/exports/{job_id}/download", tags=["Exports"])
def download_export(request, job_id: UUID) -> Any:
    """Download a completed export file as a streaming response.

    Returns:
        StreamingHttpResponse with the file content.
    """
    tenant_id = _tenant_from_request(request)
    job = get_object_or_404(ExportJob, id=job_id, tenant_id=tenant_id)

    if job.status != "completed":
        from ninja.errors import HttpError

        raise HttpError(400, f"Export job is {job.status}, not ready for download")

    return stream_export_response(job)


@router.patch("/exports/{job_id}/cancel", response=ExportOut, tags=["Exports"])
def cancel_export(request, job_id: UUID) -> ExportJob:
    """Cancel a queued or running export job."""
    tenant_id = _tenant_from_request(request)
    job = get_object_or_404(ExportJob, id=job_id, tenant_id=tenant_id)

    if job.status in ("queued", "running"):
        job.status = "cancelled"
        job.save(update_fields=["status"])

    return job


@router.delete("/exports/{job_id}", tags=["Exports"])
def delete_export(request, job_id: UUID) -> dict[str, str]:
    """Delete an export job."""
    tenant_id = _tenant_from_request(request)
    job = get_object_or_404(ExportJob, id=job_id, tenant_id=tenant_id)
    job.delete()
    return {"status": "deleted", "id": str(job_id)}


# ---------------------------------------------------------------------------
# Export presets
# ---------------------------------------------------------------------------


@router.get("/exports/presets/formats", tags=["Exports"])
def list_export_formats(request) -> dict[str, Any]:
    """List available export formats with their properties."""
    return {
        "formats": [
            {
                "key": "csv",
                "name": "CSV",
                "content_type": "text/csv; charset=utf-8",
                "extension": "csv",
                "supports_streaming": True,
                "max_recommended_rows": 1000000,
            },
            {
                "key": "json",
                "name": "JSON",
                "content_type": "application/json",
                "extension": "json",
                "supports_streaming": True,
                "max_recommended_rows": 100000,
            },
            {
                "key": "ndjson",
                "name": "Newline-Delimited JSON",
                "content_type": "application/x-ndjson",
                "extension": "ndjson",
                "supports_streaming": True,
                "max_recommended_rows": 1000000,
            },
            {
                "key": "excel",
                "name": "Excel (.xlsx)",
                "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "extension": "xlsx",
                "supports_streaming": False,
                "max_recommended_rows": 100000,
            },
        ]
    }
