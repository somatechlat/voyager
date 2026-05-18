"""Workflow trigger engine — 15 trigger types with event filtering.

Manages trigger registration, evaluation, and dispatch for all
supported trigger types: cron, webhook, platform event, metric
threshold, file upload, email, manual, state change, and more.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

from django.utils import timezone

from apps.workflows_v2.models.trigger import WorkflowTrigger
from apps.workflows_v2.models.execution import WorkflowExecution

logger = logging.getLogger(__name__)


def register_trigger(
    workflow_id: int,
    trigger_type: str,
    name: str,
    config: dict[str, Any],
    created_by: str,
) -> WorkflowTrigger:
    """Register a new trigger for a workflow.

    Args:
        workflow_id: The workflow ID to bind the trigger to.
        trigger_type: One of the 15 trigger types.
        name: Human-readable trigger name.
        config: Trigger-specific configuration.
        created_by: User ID of the creator.

    Returns:
        The created WorkflowTrigger instance.
    """
    trigger = WorkflowTrigger.objects.create(
        workflow_id=workflow_id,
        trigger_type=trigger_type,
        name=name,
        config=config,
        created_by=created_by,
    )
    logger.info("Trigger registered: %s (type=%s, workflow=%s)", trigger.id, trigger_type, workflow_id)
    return trigger


def evaluate_cron_trigger(trigger: WorkflowTrigger) -> bool:
    """Evaluate whether a cron trigger should fire now.

    Args:
        trigger: The cron trigger to evaluate.

    Returns:
        True if the trigger should fire.
    """
    try:
        import croniter  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("croniter not installed, skipping cron trigger %s", trigger.id)
        return False

    schedule = trigger.config.get("schedule", "")
    if not schedule:
        return False

    last = trigger.last_triggered_at
    now = timezone.now()

    try:
        itr = croniter.croniter(schedule, last or now)
        next_run = itr.get_next(timezone.datetime)
        # Fire if next scheduled time is within the last minute
        return next_run <= now
    except Exception as exc:
        logger.error("Cron parse error for trigger %s: %s", trigger.id, exc)
        return False


def evaluate_metric_threshold(trigger: WorkflowTrigger, metric_value: float) -> bool:
    """Evaluate whether a metric threshold trigger should fire.

    Args:
        trigger: The metric threshold trigger.
        metric_value: The current metric value.

    Returns:
        True if the threshold condition is met.
    """
    config = trigger.config
    threshold = config.get("threshold")
    operator = config.get("operator", ">=")

    if threshold is None:
        return False

    operators: dict[str, Any] = {
        ">": lambda m, t: m > t,
        ">=": lambda m, t: m >= t,
        "<": lambda m, t: m < t,
        "<=": lambda m, t: m <= t,
        "==": lambda m, t: m == t,
        "!=": lambda m, t: m != t,
    }

    op_func = operators.get(operator)
    if not op_func:
        logger.warning("Unknown operator '%s' in trigger %s", operator, trigger.id)
        return False

    return op_func(metric_value, threshold)


def evaluate_state_change_trigger(
    trigger: WorkflowTrigger,
    entity: str,
    field: str,
    old_value: Any,
    new_value: Any,
) -> bool:
    """Evaluate whether a state change trigger should fire.

    Args:
        trigger: The state change trigger.
        entity: The entity type that changed.
        field: The field that changed.
        old_value: Previous value.
        new_value: New value.

    Returns:
        True if the state change matches the trigger config.
    """
    config = trigger.config
    expected_entity = config.get("entity")
    expected_field = config.get("field")
    expected_condition = config.get("condition")

    if expected_entity and expected_entity != entity:
        return False
    if expected_field and expected_field != field:
        return False

    if expected_condition == "changed":
        return old_value != new_value
    elif expected_condition == "to_value":
        return new_value == config.get("value")
    elif expected_condition == "from_value":
        return old_value == config.get("value")

    return old_value != new_value


def handle_webhook_trigger(
    trigger: WorkflowTrigger,
    headers: dict[str, str],
    body: bytes,
) -> dict[str, Any]:
    """Process an inbound webhook trigger request.

    Validates signature if configured, parses payload, validates
    against schema, and starts workflow execution.

    Args:
        trigger: The webhook trigger configuration.
        headers: HTTP request headers.
        body: Raw request body bytes.

    Returns:
        Dict with ``status``, ``execution_id``, and optional ``error``.
    """
    config = trigger.config

    # Validate signature
    signature_secret = config.get("signatureSecret")
    if signature_secret:
        sig_header = headers.get("x-signature", headers.get("X-Signature", ""))
        expected_sig = hmac.new(
            signature_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        # Support both raw hex and 'sha256=...' prefix
        if sig_header.startswith("sha256="):
            sig_header = sig_header[7:]
        if not hmac.compare_digest(sig_header, expected_sig):
            return {"status": 401, "error": "Invalid signature"}

    # Parse payload
    content_type = config.get("contentType", "application/json")
    try:
        if content_type == "application/json":
            payload = json.loads(body) if body else {}
        else:
            payload = {"raw": body.decode("utf-8", errors="replace")}
    except json.JSONDecodeError as exc:
        return {"status": 400, "error": f"Invalid JSON payload: {exc}"}

    # Validate against schema
    payload_schema = config.get("payloadSchema")
    if payload_schema:
        valid, errors = _validate_schema(payload, payload_schema)
        if not valid:
            return {"status": 400, "error": "Invalid payload", "details": errors}

    # Start execution
    execution = WorkflowExecution.objects.create(
        workflow=trigger.workflow,
        version=trigger.workflow.version,
        status=WorkflowExecution.STATUS_PENDING,
        trigger_type=WorkflowTrigger.TYPE_WEBHOOK,
        trigger_data={"payload": payload, "headers": headers},
    )
    trigger.record_trigger()

    logger.info(
        "Webhook trigger %s started execution %s",
        trigger.id,
        execution.id,
    )
    return {"status": 200, "execution_id": execution.id}


def _validate_schema(payload: Any, schema: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a payload against a JSON schema (simplified).

    Args:
        payload: The payload to validate.
        schema: Simplified schema dict with 'required' and 'properties'.

    Returns:
        Tuple of (is_valid, list of error strings).
    """
    errors: list[str] = []

    if not isinstance(payload, dict):
        return False, ["Payload must be an object"]

    required = schema.get("required", [])
    properties = schema.get("properties", {})

    for field in required:
        if field not in payload:
            errors.append(f"Missing required field: {field}")

    for field, field_schema in properties.items():
        if field in payload:
            field_type = field_schema.get("type")
            value = payload[field]
            type_map = {
                "string": str,
                "integer": int,
                "number": (int, float),
                "boolean": bool,
                "array": list,
                "object": dict,
            }
            if field_type and field_type in type_map:
                expected = type_map[field_type]
                if not isinstance(value, expected):
                    errors.append(
                        f"Field '{field}' expected {field_type}, got {type(value).__name__}"
                    )

    return len(errors) == 0, errors


def list_active_triggers(trigger_type: str | None = None) -> list[WorkflowTrigger]:
    """List all active triggers, optionally filtered by type.

    Args:
        trigger_type: Optional trigger type filter.

    Returns:
        List of active WorkflowTrigger instances.
    """
    qs = WorkflowTrigger.objects.filter(is_active=True)
    if trigger_type:
        qs = qs.filter(trigger_type=trigger_type)
    return list(qs.select_related("workflow"))


def deactivate_trigger(trigger: WorkflowTrigger) -> None:
    """Deactivate a trigger.

    Args:
        trigger: The trigger to deactivate.
    """
    trigger.is_active = False
    trigger.save(update_fields=["is_active", "updated_at"])
    logger.info("Trigger %s deactivated", trigger.id)


def evaluate_trigger(
    trigger: WorkflowTrigger,
    event_data: dict[str, Any] | None = None,
) -> bool:
    """Evaluate a trigger against provided event data.

    Generic entry point that dispatches to the appropriate
    trigger-type-specific evaluator.

    Args:
        trigger: The trigger to evaluate.
        event_data: Optional event context data.

    Returns:
        True if the trigger should fire.
    """
    if not trigger.is_active:
        return False

    handlers: dict[str, Any] = {
        WorkflowTrigger.TYPE_CRON: evaluate_cron_trigger,
        WorkflowTrigger.TYPE_METRIC_THRESHOLD: lambda t: evaluate_metric_threshold(
            t, event_data.get("metric_value", 0) if event_data else 0
        ),
        WorkflowTrigger.TYPE_STATE_CHANGE: lambda t: evaluate_state_change_trigger(
            t,
            event_data.get("entity", "") if event_data else "",
            event_data.get("field", "") if event_data else "",
            event_data.get("old_value") if event_data else None,
            event_data.get("new_value") if event_data else None,
        ),
        WorkflowTrigger.TYPE_MANUAL: lambda t: True,
        WorkflowTrigger.TYPE_API_CALL: lambda t: True,
        WorkflowTrigger.TYPE_DATETIME: lambda t: _evaluate_datetime_trigger(t),
        WorkflowTrigger.TYPE_PLATFORM_EVENT: lambda t: _evaluate_platform_event(
            t, event_data or {}
        ),
        WorkflowTrigger.TYPE_FILE_UPLOAD: lambda t: _evaluate_file_upload_trigger(
            t, event_data or {}
        ),
        WorkflowTrigger.TYPE_EMAIL_RECEIVED: lambda t: _evaluate_email_trigger(
            t, event_data or {}
        ),
        WorkflowTrigger.TYPE_WEBSOCKET: lambda t: True,
        WorkflowTrigger.TYPE_QUEUE_MESSAGE: lambda t: True,
        WorkflowTrigger.TYPE_FORM_SUBMIT: lambda t: True,
        WorkflowTrigger.TYPE_SCHEDULED: lambda t: _evaluate_datetime_trigger(t),
        WorkflowTrigger.TYPE_RECURRING: lambda t: _evaluate_datetime_trigger(t),
        WorkflowTrigger.TYPE_WEBHOOK: lambda t: True,
    }

    handler = handlers.get(trigger.trigger_type)
    if handler:
        try:
            return handler(trigger)
        except Exception as exc:
            logger.error("Trigger evaluation error for %s: %s", trigger.id, exc)
            return False
    return False


def _evaluate_datetime_trigger(trigger: WorkflowTrigger) -> bool:
    """Evaluate a datetime trigger (one-time or recurring).

    Args:
        trigger: The datetime trigger to evaluate.

    Returns:
        True if the trigger should fire now.
    """
    config = trigger.config
    scheduled_at = config.get("scheduledAt")
    if not scheduled_at:
        return False

    try:
        from datetime import datetime

        scheduled = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
        now = timezone.now()
        # Fire if scheduled time is within the last minute
        return scheduled <= now <= (scheduled.replace(tzinfo=now.tzinfo) + timezone.timedelta(minutes=1))
    except (ValueError, TypeError) as exc:
        logger.error("Datetime parse error for trigger %s: %s", trigger.id, exc)
        return False


def _evaluate_platform_event(trigger: WorkflowTrigger, event_data: dict[str, Any]) -> bool:
    """Evaluate a platform event trigger.

    Args:
        trigger: The platform event trigger.
        event_data: The event data.

    Returns:
        True if the event matches the trigger config.
    """
    config = trigger.config
    expected_platform = config.get("platform")
    expected_event = config.get("event")

    event_platform = event_data.get("platform", "")
    event_type = event_data.get("event", "")

    if expected_platform and expected_platform != event_platform:
        return False
    if expected_event and expected_event != event_type:
        return False
    return True


def _evaluate_file_upload_trigger(
    trigger: WorkflowTrigger, event_data: dict[str, Any]
) -> bool:
    """Evaluate a file upload trigger.

    Args:
        trigger: The file upload trigger.
        event_data: The event data.

    Returns:
        True if the file upload matches the trigger config.
    """
    config = trigger.config
    expected_folder = config.get("folder", "")
    pattern = config.get("pattern", "")

    file_path = event_data.get("file_path", "")
    if expected_folder and not file_path.startswith(expected_folder):
        return False
    if pattern:
        import fnmatch

        filename = file_path.split("/")[-1] if "/" in file_path else file_path
        if not fnmatch.fnmatch(filename, pattern):
            return False
    return True


def _evaluate_email_trigger(trigger: WorkflowTrigger, event_data: dict[str, Any]) -> bool:
    """Evaluate an email received trigger.

    Args:
        trigger: The email trigger.
        event_data: The event data.

    Returns:
        True if the email matches the trigger config.
    """
    config = trigger.config
    expected_inbox = config.get("inbox", "")
    filter_rules = config.get("filterRules", {})

    if expected_inbox and event_data.get("inbox") != expected_inbox:
        return False

    from_filter = filter_rules.get("from")
    subject_filter = filter_rules.get("subject")

    if from_filter and event_data.get("from") != from_filter:
        return False
    if subject_filter and subject_filter not in event_data.get("subject", ""):
        return False

    return True
