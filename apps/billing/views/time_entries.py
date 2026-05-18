"""Time entry views.

API endpoints for time tracking, timesheet submission, and approval.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.billing.models.time_entry import TimeEntry
from apps.billing.serializers import (
    TimeEntryCreateSchema,
    TimeEntryListSchema,
    TimeEntrySchema,
    TimeEntryUpdateSchema,
    TimesheetValidationSchema,
)
from apps.billing.services.time_tracking import (
    calculate_billable_amount,
    calculate_duration,
    round_time,
    submit_timesheet,
    validate_timesheet,
)
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/time-entries", response=list[TimeEntryListSchema], tags=["Billing"])
def list_time_entries(
    request,
    client_id: int | None = None,
    project_id: int | None = None,
    user_id: str | None = None,
    status: str | None = None,
    is_billable: bool | None = None,
    week_starting: date | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List time entries with filtering."""
    tenant_id = getattr(request, "tenant_id", "")
    qs = TimeEntry.objects.filter(tenant_id=tenant_id).select_related("client", "project")
    if client_id:
        qs = qs.filter(client_id=client_id)
    if project_id:
        qs = qs.filter(project_id=project_id)
    if user_id:
        qs = qs.filter(user_id=user_id)
    if status:
        qs = qs.filter(status=status)
    if is_billable is not None:
        qs = qs.filter(is_billable=is_billable)
    if week_starting:
        qs = qs.filter(timesheet_week=week_starting)
    return list(qs.order_by("-started_at")[offset : offset + limit])


@router.get("/time-entries/{int:entry_id}", response=TimeEntrySchema, tags=["Billing"])
def get_time_entry(request, entry_id: int):
    """Get a single time entry."""
    tenant_id = getattr(request, "tenant_id", "")
    return get_object_or_404(TimeEntry, tenant_id=tenant_id, pk=entry_id)


@router.post("/time-entries", response=TimeEntrySchema, tags=["Billing"])
def create_time_entry(request, data: TimeEntryCreateSchema):
    """Create a new time entry with rounding and billing calculation."""
    tenant_id = getattr(request, "tenant_id", "")
    duration = calculate_duration(data.started_at, data.ended_at)
    rounded = round_time(duration, data.rounding_mode, data.rounding_increment)
    billable = None
    if data.billing_rate and data.is_billable:
        billable = Decimal(str(calculate_billable_amount(rounded, float(data.billing_rate))))
    entry = TimeEntry.objects.create(
        tenant_id=tenant_id,
        user_id=data.user_id,
        client_id=data.client_id,
        project_id=data.project_id,
        task_name=data.task_name,
        description=data.description,
        tracking_mode=data.tracking_mode,
        started_at=data.started_at,
        ended_at=data.ended_at,
        duration_minutes=duration,
        rounded_minutes=rounded,
        rounding_mode=data.rounding_mode,
        rounding_increment=data.rounding_increment,
        billing_rate=data.billing_rate,
        billable_amount=billable,
        is_billable=data.is_billable,
        source_data=data.source_data or {},
    )
    return entry


@router.put("/time-entries/{int:entry_id}", response=TimeEntrySchema, tags=["Billing"])
def update_time_entry(request, entry_id: int, data: TimeEntryUpdateSchema):
    """Update a time entry."""
    tenant_id = getattr(request, "tenant_id", "")
    entry = get_object_or_404(TimeEntry, tenant_id=tenant_id, pk=entry_id)
    for field, value in data.dict(exclude_unset=True).items():
        setattr(entry, field, value)
    if data.ended_at or data.started_at:
        entry.duration_minutes = calculate_duration(entry.started_at, entry.ended_at)
        entry.rounded_minutes = round_time(
            entry.duration_minutes, entry.rounding_mode, entry.rounding_increment
        )
    if entry.billing_rate and entry.is_billable:
        entry.billable_amount = Decimal(
            str(calculate_billable_amount(entry.rounded_minutes, float(entry.billing_rate)))
        )
    entry.save()
    return entry


@router.delete("/time-entries/{int:entry_id}", tags=["Billing"])
def delete_time_entry(request, entry_id: int):
    """Delete a time entry."""
    tenant_id = getattr(request, "tenant_id", "")
    entry = get_object_or_404(TimeEntry, tenant_id=tenant_id, pk=entry_id)
    entry.delete()
    return {"deleted": True, "entry_id": entry_id}


@router.post("/time-entries/{int:entry_id}/submit", response=dict, tags=["Billing"])
def submit_entry(request, entry_id: int):
    """Submit a single time entry for approval."""
    tenant_id = getattr(request, "tenant_id", "")
    entry = get_object_or_404(TimeEntry, tenant_id=tenant_id, pk=entry_id)
    entry.status = TimeEntry.Status.SUBMITTED
    entry.save(update_fields=["status", "updated_at"])
    return {"submitted": True, "entry_id": entry_id, "status": entry.status}


@router.post("/time-entries/{int:entry_id}/approve", response=dict, tags=["Billing"])
def approve_entry(request, entry_id: int):
    """Approve a time entry."""
    tenant_id = getattr(request, "tenant_id", "")
    approver_id = getattr(request, "user_id", "")
    entry = get_object_or_404(TimeEntry, tenant_id=tenant_id, pk=entry_id)
    entry.status = TimeEntry.Status.APPROVED
    entry.approver_id = approver_id
    entry.approved_at = datetime.now()
    entry.save(update_fields=["status", "approver_id", "approved_at", "updated_at"])
    return {"approved": True, "entry_id": entry_id, "approver_id": approver_id}


@router.post("/time-entries/{int:entry_id}/reject", response=dict, tags=["Billing"])
def reject_entry(request, entry_id: int, reason: str = ""):
    """Reject a time entry."""
    tenant_id = getattr(request, "tenant_id", "")
    approver_id = getattr(request, "user_id", "")
    entry = get_object_or_404(TimeEntry, tenant_id=tenant_id, pk=entry_id)
    entry.status = TimeEntry.Status.REJECTED
    entry.approver_id = approver_id
    entry.rejection_reason = reason
    entry.save(update_fields=["status", "approver_id", "rejection_reason", "updated_at"])
    return {"rejected": True, "entry_id": entry_id, "reason": reason}


@router.post("/timesheets/validate", response=TimesheetValidationSchema, tags=["Billing"])
def validate_timesheet_endpoint(
    request,
    user_id: str,
    week_starting: date,
):
    """Validate a timesheet for a user and week."""
    tenant_id = getattr(request, "tenant_id", "")
    result = validate_timesheet(tenant_id, user_id, week_starting)
    return result


@router.post("/timesheets/submit", response=dict, tags=["Billing"])
def submit_timesheet_endpoint(
    request,
    user_id: str,
    week_starting: date,
):
    """Submit all draft entries for a timesheet week."""
    tenant_id = getattr(request, "tenant_id", "")
    return submit_timesheet(tenant_id, user_id, week_starting)
