"""Automation sequence management views."""

from __future__ import annotations

import logging
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.email_marketing.models.sequence import AutomationSequence
from apps.email_marketing.models.subscriber import EmailSubscriber
from apps.email_marketing.serializers import (
    AutomationSequenceCreateSchema,
    AutomationSequenceDetailSchema,
    AutomationSequenceListSchema,
    AutomationSequenceUpdateSchema,
    AutomationTriggerSchema,
    SequenceEvaluateSchema,
)
from apps.email_marketing.services.automation import (
    evaluate_sequence_step,
    process_trigger,
)

logger = logging.getLogger(__name__)

router = Router()


@router.get("/", response=list[AutomationSequenceListSchema])
def list_sequences(
    request,
    tenant_id: str = "",
    trigger_type: str = "",
    status: str = "",
    search: str = "",
    limit: int = 50,
    offset: int = 0,
) -> list[AutomationSequence]:
    """List automation sequences with optional filtering.

    Args:
        request: HTTP request.
        tenant_id: Filter by tenant.
        trigger_type: Filter by trigger type.
        status: Filter by status.
        search: Search in name.
        limit: Page size.
        offset: Pagination offset.

    Returns:
        List of automation sequences.
    """
    qs = AutomationSequence.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if trigger_type:
        qs = qs.filter(trigger_type=trigger_type)
    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(name__icontains=search)
    return list(qs.order_by("-created_at")[offset : offset + limit])


@router.post("/", response=AutomationSequenceDetailSchema)
def create_sequence(
    request,
    payload: AutomationSequenceCreateSchema,
) -> AutomationSequence:
    """Create a new automation sequence.

    Args:
        request: HTTP request.
        payload: Sequence creation data.

    Returns:
        Created sequence.
    """
    data = payload.dict()
    sequence = AutomationSequence.objects.create(**data)
    logger.info("Sequence %s created for tenant %s", sequence.id, sequence.tenant_id)
    return sequence


@router.get("/{sequence_id}", response=AutomationSequenceDetailSchema)
def get_sequence(
    request,
    sequence_id: int,
) -> AutomationSequence:
    """Get a single automation sequence.

    Args:
        request: HTTP request.
        sequence_id: Sequence primary key.

    Returns:
        Automation sequence.
    """
    return get_object_or_404(AutomationSequence, id=sequence_id)


@router.put("/{sequence_id}", response=AutomationSequenceDetailSchema)
def update_sequence(
    request,
    sequence_id: int,
    payload: AutomationSequenceUpdateSchema,
) -> AutomationSequence:
    """Update an automation sequence.

    Args:
        request: HTTP request.
        sequence_id: Sequence primary key.
        payload: Update data.

    Returns:
        Updated sequence.
    """
    sequence = get_object_or_404(AutomationSequence, id=sequence_id)
    data = payload.dict(exclude_unset=True)
    for attr, val in data.items():
        setattr(sequence, attr, val)
    sequence.save()
    return sequence


@router.delete("/{sequence_id}")
def delete_sequence(
    request,
    sequence_id: int,
) -> dict[str, bool]:
    """Delete an automation sequence.

    Args:
        request: HTTP request.
        sequence_id: Sequence primary key.

    Returns:
        Success dict.
    """
    sequence = get_object_or_404(AutomationSequence, id=sequence_id)
    sequence.delete()
    return {"success": True}


@router.post("/{sequence_id}/activate")
def activate_sequence(
    request,
    sequence_id: int,
) -> dict[str, Any]:
    """Activate a draft sequence.

    Args:
        request: HTTP request.
        sequence_id: Sequence primary key.

    Returns:
        Activation result.
    """
    sequence = get_object_or_404(AutomationSequence, id=sequence_id)
    sequence.status = AutomationSequence.Status.ACTIVE
    sequence.save(update_fields=["status"])
    return {"success": True, "sequence_id": str(sequence.id), "status": sequence.status}


@router.post("/{sequence_id}/pause")
def pause_sequence(
    request,
    sequence_id: int,
) -> dict[str, Any]:
    """Pause an active sequence.

    Args:
        request: HTTP request.
        sequence_id: Sequence primary key.

    Returns:
        Pause result.
    """
    sequence = get_object_or_404(AutomationSequence, id=sequence_id)
    sequence.status = AutomationSequence.Status.PAUSED
    sequence.save(update_fields=["status"])
    return {"success": True, "sequence_id": str(sequence.id), "status": sequence.status}


@router.post("/{sequence_id}/test-trigger")
def test_trigger(
    request,
    sequence_id: int,
    payload: AutomationTriggerSchema,
) -> dict[str, Any]:
    """Test a trigger against a subscriber.

    Args:
        request: HTTP request.
        sequence_id: Sequence primary key.
        payload: Trigger test data.

    Returns:
        Trigger evaluation result.
    """
    sequence = get_object_or_404(AutomationSequence, id=sequence_id)
    subscriber = get_object_or_404(EmailSubscriber, id=payload.subscriber_id)
    result = process_trigger(
        trigger_type=sequence.trigger_type,
        trigger_config=sequence.trigger_config,
        subscriber=subscriber,
        event_data=payload.event_data or {},
    )
    return {
        "triggered": result,
        "trigger_type": sequence.trigger_type,
        "subscriber_id": str(subscriber.id),
    }


@router.post("/{sequence_id}/evaluate-step")
def evaluate_step(
    request,
    sequence_id: int,
    payload: SequenceEvaluateSchema,
) -> dict[str, Any]:
    """Evaluate a sequence step for a subscriber.

    Args:
        request: HTTP request.
        sequence_id: Sequence primary key.
        payload: Evaluation data.

    Returns:
        Step evaluation result.
    """
    sequence = get_object_or_404(AutomationSequence, id=sequence_id)
    subscriber = get_object_or_404(EmailSubscriber, id=payload.subscriber_id)
    steps = sequence.steps or []
    step = None
    for s in steps:
        if s.get("id") == payload.step_id:
            step = s
            break
    if step is None:
        return {"error": "Step not found in sequence"}
    result = evaluate_sequence_step(
        step=step,
        subscriber=subscriber,
        sequence_state={"steps": steps, "current_step_id": payload.step_id},
        event_data=payload.event_data or {},
    )
    return result


@router.post("/{sequence_id}/duplicate", response=AutomationSequenceDetailSchema)
def duplicate_sequence(
    request,
    sequence_id: int,
) -> AutomationSequence:
    """Duplicate an automation sequence.

    Args:
        request: HTTP request.
        sequence_id: Sequence primary key.

    Returns:
        New duplicated sequence.
    """
    sequence = get_object_or_404(AutomationSequence, id=sequence_id)
    sequence.pk = None
    sequence.name = f"{sequence.name} (Copy)"
    sequence.status = AutomationSequence.Status.DRAFT
    sequence.total_enrolled = 0
    sequence.total_completed = 0
    sequence.total_exited = 0
    sequence.save()
    return sequence
