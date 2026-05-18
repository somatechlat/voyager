"""Strategy module serializers (Ninja schemas).

Input/output models for audience personas, competitor analysis,
content strategy, editorial calendar, OKR tracking, and market research.
"""

from __future__ import annotations

from .personas import (
    AggregatedTargetingOut,
    ChannelRankingIn,
    DemographicsIn,
    PersonaCampaignLinkIn,
    PersonaCampaignLinkOut,
    PersonaFilter,
    PersonaIn,
    PersonaOut,
    PsychographicsIn,
)
from .competitors import (
    CompetitorContentIn,
    CompetitorContentOut,
    CompetitorFilter,
    CompetitorIn,
    CompetitorOut,
    ScrapingConfigIn,
    SocialProfilesIn,
    SWOTOut,
    ThemeOut,
)
from .strategy import (
    ContentStrategyIn,
    ContentStrategyOut,
    FormatMixIn,
    FormatMixOut,
    GoalMappingOut,
    StrategyFilter,
    TopicClusterIn,
    TopicClusterOut,
)
from .calendar import (
    CalendarEntryIn,
    CalendarEntryOut,
    CalendarFilter,
    PipelineSummaryOut,
    StatusTransitionIn,
    WorkloadOut,
)
from .okr import (
    ConfidenceSummaryOut,
    KeyResultIn,
    KeyResultOut,
    ObjectiveIn,
    ObjectiveOut,
    ObjectiveTreeOut,
    OKRFilter,
    ProgressOut,
    ProgressUpdateIn,
)
from .research import (
    CompetitiveLandscapeOut,
    MarketResearchIn,
    MarketResearchOut,
    ResearchFilter,
    TrendDetectionIn,
    TrendOut,
)

__all__ = [
    # Personas
    "AggregatedTargetingOut",
    "ChannelRankingIn",
    "DemographicsIn",
    "PersonaCampaignLinkIn",
    "PersonaCampaignLinkOut",
    "PersonaFilter",
    "PersonaIn",
    "PersonaOut",
    "PsychographicsIn",
    # Competitors
    "CompetitorContentIn",
    "CompetitorContentOut",
    "CompetitorFilter",
    "CompetitorIn",
    "CompetitorOut",
    "ScrapingConfigIn",
    "SocialProfilesIn",
    "SWOTOut",
    "ThemeOut",
    # Strategy
    "ContentStrategyIn",
    "ContentStrategyOut",
    "FormatMixIn",
    "FormatMixOut",
    "GoalMappingOut",
    "StrategyFilter",
    "TopicClusterIn",
    "TopicClusterOut",
    # Calendar
    "CalendarEntryIn",
    "CalendarEntryOut",
    "CalendarFilter",
    "PipelineSummaryOut",
    "StatusTransitionIn",
    "WorkloadOut",
    # OKR
    "ConfidenceSummaryOut",
    "KeyResultIn",
    "KeyResultOut",
    "ObjectiveIn",
    "ObjectiveOut",
    "ObjectiveTreeOut",
    "OKRFilter",
    "ProgressOut",
    "ProgressUpdateIn",
    # Research
    "CompetitiveLandscapeOut",
    "MarketResearchIn",
    "MarketResearchOut",
    "ResearchFilter",
    "TrendDetectionIn",
    "TrendOut",
]
