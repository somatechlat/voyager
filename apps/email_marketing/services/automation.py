"""Automation sequence engine service.

Handles trigger evaluation, step processing, condition branching,
and goal tracking for email automation sequences.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from apps.email_marketing.models.sequence import AutomationSequence
from apps.email_marketing.models.subscriber import EmailSubscriber

# ---------------------------------------------------------------------------
# Trigger processing
# ---------------------------------------------------------------------------


def process_trigger(
    trigger_type: str,
    trigger_config: dict[str, Any],
    subscriber: EmailSubscriber,
    event_data: dict[str, Any] | None = None,
) -> bool:
    """Evaluate whether a trigger condition is met.

    Args:
        trigger_type: Type of trigger (list_signup, purchase, etc.).
        trigger_config: Trigger-specific configuration.
        subscriber: The subscriber to evaluate against.
        event_data: Optional event payload from webhook/API.

    Returns:
        True if the trigger condition is met.
    """
    trigger_map = {
        AutomationSequence.TriggerType.LIST_SIGNUP: _trigger_list_signup,
        AutomationSequence.TriggerType.TAG_ADDED: _trigger_tag_added,
        AutomationSequence.TriggerType.PURCHASE: _trigger_purchase,
        AutomationSequence.TriggerType.EMAIL_ACTION: _trigger_email_action,
        AutomationSequence.TriggerType.SCORE_CHANGE: _trigger_score_change,
        AutomationSequence.TriggerType.API_EVENT: _trigger_api_event,
        AutomationSequence.TriggerType.BEHAVIOR: _trigger_behavior,
        AutomationSequence.TriggerType.DATE: _trigger_date,
        AutomationSequence.TriggerType.ABANDONED_CART: _trigger_abandoned_cart,
        AutomationSequence.TriggerType.PAGE_VISIT: _trigger_page_visit,
    }
    handler = trigger_map.get(trigger_type)
    if handler is None:
        return False
    return handler(trigger_config, subscriber, event_data or {})


def _trigger_list_signup(
    config: dict[str, Any],
    subscriber: EmailSubscriber,
    event_data: dict[str, Any],
) -> bool:
    """Evaluate list signup trigger."""
    list_id = config.get("list_id")
    if list_id and event_data.get("list_id") != list_id:
        return False
    double_optin = config.get("double_optin", False)
    if double_optin and not event_data.get("confirmed", False):
        return False
    return subscriber.status == EmailSubscriber.Status.ACTIVE


def _trigger_tag_added(
    config: dict[str, Any],
    subscriber: EmailSubscriber,
    event_data: dict[str, Any],
) -> bool:
    """Evaluate tag added trigger."""
    tag = config.get("tag")
    tags = subscriber.tags or []
    if isinstance(tags, str):
        tags = [tags]
    triggered_tag = event_data.get("tag", tag)
    if triggered_tag:
        return triggered_tag in tags
    return bool(tag) and tag in tags


def _trigger_purchase(
    config: dict[str, Any],
    subscriber: EmailSubscriber,
    event_data: dict[str, Any],
) -> bool:
    """Evaluate purchase trigger."""
    product_id = config.get("product_id")
    category = config.get("category")
    if product_id and event_data.get("product_id") != product_id:
        return False
    if category and event_data.get("category") != category:
        return False
    return True


def _trigger_email_action(
    config: dict[str, Any],
    subscriber: EmailSubscriber,
    event_data: dict[str, Any],
) -> bool:
    """Evaluate email action trigger (open, click, no-open)."""
    action = config.get("action", "opened")
    campaign_id = config.get("campaign_id")
    if campaign_id and event_data.get("campaign_id") != campaign_id:
        return False
    if action == "opened":
        return subscriber.open_count > 0
    if action == "clicked":
        return subscriber.click_count > 0
    if action == "no_open":
        return subscriber.open_count == 0
    if action == "no_click":
        return subscriber.click_count == 0
    return False


def _trigger_score_change(
    config: dict[str, Any],
    subscriber: EmailSubscriber,
    event_data: dict[str, Any],
) -> bool:
    """Evaluate score change trigger."""
    threshold = config.get("threshold", 80)
    direction = config.get("direction", "above")
    score = float(subscriber.engagement_score)
    if direction == "above":
        return score >= threshold
    return score <= threshold


def _trigger_api_event(
    config: dict[str, Any],
    subscriber: EmailSubscriber,
    event_data: dict[str, Any],
) -> bool:
    """Evaluate API/webhook event trigger."""
    event_name = config.get("event_name")
    if event_name and event_data.get("event") != event_name:
        return False
    conditions = config.get("conditions", {})
    for key, expected in conditions.items():
        if event_data.get(key) != expected:
            return False
    return True


def _trigger_behavior(
    config: dict[str, Any],
    subscriber: EmailSubscriber,
    event_data: dict[str, Any],
) -> bool:
    """Evaluate behavioral trigger."""
    event = config.get("event")
    min_count = config.get("min_count", 1)
    if event_data.get("event") != event:
        return False
    return event_data.get("count", 0) >= min_count


def _trigger_date(
    config: dict[str, Any],
    subscriber: EmailSubscriber,
    event_data: dict[str, Any],
) -> bool:
    """Evaluate date-based trigger (e.g. birthday, anniversary)."""
    date_field = config.get("date_field")
    offset_days = config.get("offset_days", 0)
    if not date_field:
        return False
    subscriber_date = subscriber.custom_fields.get(date_field) if subscriber.custom_fields else None
    if event_data.get("date"):
        subscriber_date = event_data["date"]
    if not subscriber_date:
        return False
    try:
        check_date = datetime.now(UTC).date() + timedelta(days=offset_days)
        target = datetime.strptime(str(subscriber_date), "%Y-%m-%d").date()
        return target.month == check_date.month and target.day == check_date.day
    except (ValueError, TypeError):
        return False


def _trigger_abandoned_cart(
    config: dict[str, Any],
    subscriber: EmailSubscriber,
    event_data: dict[str, Any],
) -> bool:
    """Evaluate abandoned cart trigger."""
    hours = config.get("hours_since_abandon", 1)
    return event_data.get("event") == "cart_abandoned" and event_data.get("hours", 0) >= hours


def _trigger_page_visit(
    config: dict[str, Any],
    subscriber: EmailSubscriber,
    event_data: dict[str, Any],
) -> bool:
    """Evaluate page visit trigger."""
    page_url = config.get("page_url")
    min_visits = config.get("min_visits", 1)
    if page_url and event_data.get("page") != page_url:
        return False
    return event_data.get("visits", 0) >= min_visits


# ---------------------------------------------------------------------------
# Step evaluation
# ---------------------------------------------------------------------------


def evaluate_sequence_step(
    step: dict[str, Any],
    subscriber: EmailSubscriber,
    sequence_state: dict[str, Any],
    event_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate a single sequence step and determine next action.

    Args:
        step: The step definition.
        subscriber: The subscriber currently in the sequence.
        sequence_state: Current sequence state (current_step_id, history, etc.).
        event_data: Optional event data for condition evaluation.

    Returns:
        Dict with action type and next step info.
    """
    step_type = step.get("type", "email")
    step_id = step.get("id", "")
    if step_type == "email":
        return {
            "action": "send_email",
            "step_id": step_id,
            "template_id": step.get("template_id"),
            "next_step": _find_next_step_id(step, sequence_state),
        }
    if step_type == "delay":
        duration = step.get("duration", {})
        delay_seconds = _parse_duration(duration)
        return {
            "action": "wait",
            "step_id": step_id,
            "delay_seconds": delay_seconds,
            "resume_at": (datetime.now(UTC) + timedelta(seconds=delay_seconds)).isoformat(),
            "next_step": _find_next_step_id(step, sequence_state),
        }
    if step_type == "condition":
        condition = step.get("condition", {})
        result = check_condition(condition, subscriber, event_data or {})
        branch_key = "trueBranch" if result else "falseBranch"
        return {
            "action": "branch",
            "step_id": step_id,
            "condition_result": result,
            "next_step": step.get(branch_key),
        }
    if step_type == "goal":
        achieved = should_exit_sequence(step, subscriber, event_data or {})
        return {
            "action": "check_goal",
            "step_id": step_id,
            "goal_achieved": achieved,
            "exit": achieved and step.get("exit_on_achieve", False),
            "next_step": (
                None
                if (achieved and step.get("exit_on_achieve"))
                else _find_next_step_id(step, sequence_state)
            ),
        }
    return {"action": "unknown", "step_id": step_id, "next_step": None}


def check_condition(
    condition: dict[str, Any],
    subscriber: EmailSubscriber,
    event_data: dict[str, Any],
) -> bool:
    """Evaluate a condition against subscriber data.

    Args:
        condition: Condition dict with field, operator, value.
        subscriber: The subscriber.
        event_data: Event data for context.

    Returns:
        True if condition is met.
    """
    field = condition.get("field", "")
    operator = condition.get("operator", "eq")
    value = condition.get("value")
    _ = condition.get("within", "")
    if field == "email_action":
        action_type = condition.get("operator", "opened")
        _ = value
        if action_type == "opened":
            return subscriber.open_count > 0
        if action_type == "clicked":
            return subscriber.click_count > 0
        if action_type == "not_opened":
            return subscriber.open_count == 0
        return False
    if field == "tag":
        tags = subscriber.tags or []
        if isinstance(tags, str):
            tags = [tags]
        if operator == "has":
            return value in tags
        if operator == "not_has":
            return value not in tags
    if field == "engagement_score":
        score = float(subscriber.engagement_score)
        if operator == "gte":
            return score >= value
        if operator == "lte":
            return score <= value
        if operator == "eq":
            return score == value
    if field == "status":
        if operator == "eq":
            return subscriber.status == value
        if operator == "neq":
            return subscriber.status != value
    if field.startswith("custom."):
        custom_key = field.replace("custom.", "")
        custom_value = (
            subscriber.custom_fields.get(custom_key) if subscriber.custom_fields else None
        )
        if operator == "eq":
            return custom_value == value
        if operator == "has":
            return bool(custom_value) and value in str(custom_value)
    return False


def should_exit_sequence(
    goal_step: dict[str, Any],
    subscriber: EmailSubscriber,
    event_data: dict[str, Any],
) -> bool:
    """Check if a goal step has been achieved.

    Args:
        goal_step: The goal step definition.
        subscriber: The subscriber.
        event_data: Event data.

    Returns:
        True if the goal is achieved.
    """
    goal_type = goal_step.get("goal_type", "")
    if goal_type == "purchase":
        return event_data.get("event") == "purchase" or subscriber.rfm_monetary > 0
    if goal_type == "click":
        return subscriber.click_count > 0
    if goal_type == "open":
        return subscriber.open_count > 0
    if goal_type == "engagement_score":
        threshold = goal_step.get("threshold", 80)
        return float(subscriber.engagement_score) >= threshold
    return False


def _find_next_step_id(
    current_step: dict[str, Any],
    sequence_state: dict[str, Any],
) -> str | None:
    """Find the ID of the step after the current one.

    Args:
        current_step: The current step definition.
        sequence_state: Sequence state with step list.

    Returns:
        Next step ID or None.
    """
    steps = sequence_state.get("steps", [])
    current_id = current_step.get("id")
    for i, step in enumerate(steps):
        if step.get("id") == current_id and i + 1 < len(steps):
            return steps[i + 1].get("id")
    return None


def _parse_duration(duration: dict[str, Any]) -> int:
    """Parse a duration dict to seconds.

    Args:
        duration: Dict with ``value`` and ``unit``.

    Returns:
        Duration in seconds.
    """
    value = int(duration.get("value", 0))
    unit = duration.get("unit", "hours")
    multipliers = {
        "seconds": 1,
        "minutes": 60,
        "hours": 3600,
        "days": 86400,
        "weeks": 604800,
    }
    return value * multipliers.get(unit, 3600)
