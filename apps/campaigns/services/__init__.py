"""Campaign services package.

Exports all campaign management services for business logic.
"""

from apps.campaigns.services.lifecycle import (
    auto_advance_if_eligible,
    get_available_stages,
    transition_stage,
    validate_transition,
)
from apps.campaigns.services.channels import (
    build_dependency_graph,
    find_critical_path,
    get_channel_recommendations,
    has_cycle,
    schedule_channels,
    topological_sort,
)
from apps.campaigns.services.ab_testing import (
    calculate_sample_size,
    compute_and_save_sample_size,
    evaluate_test_results,
    select_winner,
)
from apps.campaigns.services.budget import (
    calculate_pacing,
    check_budget_alerts,
    record_allocation,
    record_spend,
)
from apps.campaigns.services.performance import (
    calculate_roi,
    get_campaign_summary,
    get_channel_performance,
    get_dashboard_kpis,
    get_time_series,
)
from apps.campaigns.services.briefs import generate_brief

__all__ = [
    # lifecycle
    "transition_stage",
    "validate_transition",
    "get_available_stages",
    "auto_advance_if_eligible",
    # channels
    "build_dependency_graph",
    "has_cycle",
    "topological_sort",
    "find_critical_path",
    "schedule_channels",
    "get_channel_recommendations",
    # ab_testing
    "calculate_sample_size",
    "evaluate_test_results",
    "select_winner",
    "compute_and_save_sample_size",
    # budget
    "calculate_pacing",
    "check_budget_alerts",
    "record_spend",
    "record_allocation",
    # performance
    "get_campaign_summary",
    "get_channel_performance",
    "get_time_series",
    "get_dashboard_kpis",
    "calculate_roi",
    # briefs
    "generate_brief",
]
