"""Campaign lifecycle service — 8-stage transitions with validation.

Manages campaign progression through Planning → Brief → Creative →
Approval → Launch → Monitoring → Optimization → Reporting → Archived.
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction

from apps.campaigns.models import Campaign

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stage transition graph (valid directed edges)
# ---------------------------------------------------------------------------
VALID_TRANSITIONS: dict[str, list[str]] = {
    Campaign.Stage.PLANNING: [Campaign.Stage.BRIEF],
    Campaign.Stage.BRIEF: [Campaign.Stage.PLANNING, Campaign.Stage.CREATIVE],
    Campaign.Stage.CREATIVE: [Campaign.Stage.BRIEF, Campaign.Stage.APPROVAL],
    Campaign.Stage.APPROVAL: [Campaign.Stage.CREATIVE, Campaign.Stage.LAUNCH],
    Campaign.Stage.LAUNCH: [Campaign.Stage.MONITORING],
    Campaign.Stage.MONITORING: [Campaign.Stage.OPTIMIZATION, Campaign.Stage.REPORTING],
    Campaign.Stage.OPTIMIZATION: [Campaign.Stage.MONITORING, Campaign.Stage.REPORTING],
    Campaign.Stage.REPORTING: ["archived"],
}

# ---------------------------------------------------------------------------
# Required fields per target stage
# ---------------------------------------------------------------------------
STAGE_REQUIREMENTS: dict[str, list[str]] = {
    Campaign.Stage.PLANNING: ["name", "objective", "budget"],
    Campaign.Stage.BRIEF: [
        "name",
        "objective",
        "budget",
        "start_date",
        "end_date",
        "target_audience",
        "channels",
    ],
    Campaign.Stage.CREATIVE: ["name", "brief_approved"],
    Campaign.Stage.APPROVAL: ["name", "all_creatives_approved"],
    Campaign.Stage.LAUNCH: ["name", "approval_status"],
    Campaign.Stage.MONITORING: ["name", "all_platforms_published"],
    Campaign.Stage.OPTIMIZATION: ["name"],
    Campaign.Stage.REPORTING: ["name"],
    "archived": ["name"],
}

# ---------------------------------------------------------------------------
# Stage enter hooks — side effects when entering a stage
# ---------------------------------------------------------------------------
_STAGE_ENTER_HOOKS: dict[str, Any] = {}


def register_stage_hook(stage: str, func: Any) -> None:
    """Register a hook to run when entering a stage.

    Args:
        stage: The stage identifier.
        func: Callable that receives the campaign instance.
    """
    _STAGE_ENTER_HOOKS[stage] = func


def _get_stage_field_value(campaign: Campaign, field: str) -> Any:
    """Get a field value from campaign, handling nested checks.

    Args:
        campaign: The campaign instance.
        field: Field name to check.

    Returns:
        The field value.
    """
    if field == "brief_approved":
        return campaign.brief_approved
    if field == "all_creatives_approved":
        return campaign.all_creatives_approved
    if field == "approval_status":
        return campaign.approval_status
    if field == "all_platforms_published":
        return campaign.all_platforms_published
    return getattr(campaign, field, None)


def _validate_required_fields(campaign: Campaign, target_stage: str) -> list[str]:
    """Check that all required fields for a stage are present.

    Args:
        campaign: The campaign to validate.
        target_stage: The target stage.

    Returns:
        List of missing field names (empty if all present).
    """
    missing: list[str] = []
    required = STAGE_REQUIREMENTS.get(target_stage, [])
    for field in required:
        value = _get_stage_field_value(campaign, field)
        if field == "approval_status":
            if value != Campaign.ApprovalStatus.APPROVED:
                missing.append(f"{field}=approved")
        elif field == "brief_approved":
            if not value:
                missing.append(f"{field}=true")
        elif field == "all_creatives_approved":
            if not value:
                missing.append(f"{field}=true")
        elif field == "all_platforms_published":
            if not value:
                missing.append(f"{field}=true")
        elif value is None or value == "":
            missing.append(field)
        elif isinstance(value, (list, dict)) and not value:
            missing.append(field)
    return missing


def validate_transition(campaign: Campaign, target_stage: str) -> dict[str, Any]:
    """Validate whether a stage transition is allowed.

    Args:
        campaign: The campaign to transition.
        target_stage: The desired target stage.

    Returns:
        Dict with keys: valid (bool), errors (list of str).
    """
    errors: list[str] = []
    current = campaign.stage

    if target_stage == current:
        return {"valid": True, "errors": []}

    valid_targets = VALID_TRANSITIONS.get(current, [])
    if target_stage not in valid_targets:
        errors.append(
            f"Cannot transition from '{current}' to '{target_stage}'. "
            f"Valid targets: {', '.join(valid_targets)}"
        )
        return {"valid": False, "errors": errors}

    missing = _validate_required_fields(campaign, target_stage)
    if missing:
        errors.append(f"Missing required fields for '{target_stage}': {', '.join(missing)}")

    return {"valid": not errors, "errors": errors}


@transaction.atomic
def transition_stage(
    campaign: Campaign,
    target_stage: str,
    triggered_by: str | None = None,
) -> dict[str, Any]:
    """Execute a validated stage transition.

    Args:
        campaign: The campaign to transition.
        target_stage: The desired target stage.
        triggered_by: Optional user/system identifier.

    Returns:
        Result dict with success, previous_stage, new_stage, errors.
    """
    validation = validate_transition(campaign, target_stage)
    if not validation["valid"]:
        return {
            "success": False,
            "previous_stage": campaign.stage,
            "new_stage": campaign.stage,
            "errors": validation["errors"],
        }

    previous = campaign.stage

    # Run stage enter hook if registered
    hook = _STAGE_ENTER_HOOKS.get(target_stage)
    if hook:
        hook(campaign)

    campaign.stage = target_stage

    # Auto-update status for certain transitions
    if target_stage == Campaign.Stage.LAUNCH:
        campaign.status = Campaign.Status.ACTIVE
    elif target_stage == Campaign.Stage.REPORTING:
        campaign.status = Campaign.Status.COMPLETED
    elif target_stage == "archived":
        campaign.status = Campaign.Status.ARCHIVED
        target_stage = Campaign.Stage.REPORTING
        campaign.stage = target_stage

    campaign.save(update_fields=["stage", "status", "updated_at"])

    logger.info(
        "Campaign %s stage transition: %s -> %s (triggered_by=%s)",
        campaign.id,
        previous,
        target_stage,
        triggered_by,
    )

    return {
        "success": True,
        "previous_stage": previous,
        "new_stage": target_stage,
        "errors": [],
    }


def get_available_stages(campaign: Campaign) -> list[dict[str, Any]]:
    """Get list of available next stages with validation status.

    Args:
        campaign: The campaign to check.

    Returns:
        List of dicts with stage, label, valid, errors for each possible stage.
    """
    current = campaign.stage
    targets = VALID_TRANSITIONS.get(current, [])
    result: list[dict[str, Any]] = []
    stage_labels = dict(Campaign.Stage.choices)

    for target in targets:
        validation = validate_transition(campaign, target)
        result.append(
            {
                "stage": target,
                "label": stage_labels.get(target, target),
                "valid": validation["valid"],
                "errors": validation["errors"],
            }
        )
    return result


def auto_advance_if_eligible(campaign: Campaign) -> dict[str, Any]:
    """Check if campaign can auto-advance based on trigger conditions.

    Evaluates auto-advance rules for the current stage:
    - brief -> creative: brief_approved = true
    - creative -> approval: all_creatives_approved = true
    - approval -> launch: approval_status = 'approved'
    - launch -> monitoring: all_platforms_published = true
    - reporting -> archived: end_date reached

    Args:
        campaign: The campaign to check.

    Returns:
        Auto-advance result, or no-op if not eligible.
    """
    current = campaign.stage

    auto_rules: dict[str, Any] = {
        Campaign.Stage.BRIEF: lambda c: c.brief_approved,
        Campaign.Stage.CREATIVE: lambda c: c.all_creatives_approved,
        Campaign.Stage.APPROVAL: lambda c: c.approval_status == Campaign.ApprovalStatus.APPROVED,
        Campaign.Stage.LAUNCH: lambda c: c.all_platforms_published,
    }

    rule = auto_rules.get(current)
    if rule and rule(campaign):
        next_stages = VALID_TRANSITIONS.get(current, [])
        if next_stages:
            # Prefer forward progression (not going back to planning from brief)
            forward = [s for s in next_stages if s != Campaign.Stage.PLANNING]
            target = forward[0] if forward else next_stages[0]
            return transition_stage(campaign, target, triggered_by="auto")

    # Check if campaign end date reached -> move to reporting
    from datetime import date

    if (
        current != Campaign.Stage.REPORTING
        and campaign.end_date
        and date.today() > campaign.end_date
        and current in (Campaign.Stage.MONITORING, Campaign.Stage.OPTIMIZATION)
    ):
        return transition_stage(campaign, Campaign.Stage.REPORTING, triggered_by="auto")

    return {"success": False, "previous_stage": current, "new_stage": current, "errors": []}
