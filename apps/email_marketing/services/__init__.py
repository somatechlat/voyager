"""Email Marketing services package.

Business logic services for the email marketing module.
"""

from apps.email_marketing.services.ab_testing import (
    calculate_lift,
    calculate_sample_size,
    chi_squared_test,
    select_winner,
)
from apps.email_marketing.services.analytics import (
    aggregate_campaign_analytics,
    compute_device_breakdown,
    compute_engagement_tiers,
    generate_click_heatmap,
)
from apps.email_marketing.services.automation import (
    check_condition,
    evaluate_sequence_step,
    process_trigger,
    should_exit_sequence,
)
from apps.email_marketing.services.campaigns import (
    get_campaign_recipients,
    schedule_campaign,
    update_campaign_stats,
    validate_campaign_ready,
)
from apps.email_marketing.services.deliverability import (
    HARD_BOUNCE_CODES,
    SOFT_BOUNCE_CODES,
    calculate_reputation_score,
    check_authentication,
    classify_bounce,
    generate_recommendations,
)
from apps.email_marketing.services.segments import (
    calculate_rfm_scores,
    evaluate_dynamic_segment,
    evaluate_predictive_segment,
    refresh_segment_count,
)
from apps.email_marketing.services.templates import (
    BLOCK_REGISTRY,
    generate_plain_text,
    generate_responsive_css,
    render_template_html,
    test_compatibility,
)

__all__ = [
    "render_template_html",
    "generate_responsive_css",
    "generate_plain_text",
    "test_compatibility",
    "BLOCK_REGISTRY",
    "schedule_campaign",
    "validate_campaign_ready",
    "get_campaign_recipients",
    "update_campaign_stats",
    "process_trigger",
    "evaluate_sequence_step",
    "check_condition",
    "should_exit_sequence",
    "evaluate_dynamic_segment",
    "calculate_rfm_scores",
    "evaluate_predictive_segment",
    "refresh_segment_count",
    "classify_bounce",
    "calculate_reputation_score",
    "check_authentication",
    "generate_recommendations",
    "HARD_BOUNCE_CODES",
    "SOFT_BOUNCE_CODES",
    "calculate_sample_size",
    "chi_squared_test",
    "select_winner",
    "calculate_lift",
    "aggregate_campaign_analytics",
    "generate_click_heatmap",
    "compute_engagement_tiers",
    "compute_device_breakdown",
]
