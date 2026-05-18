"""Strategy module views.

Ninja router views for personas, competitors, content strategy,
editorial calendar, OKR tracking, and market research.
"""

from __future__ import annotations

from .calendar import router as calendar_router
from .competitors import router as competitors_router
from .okr import router as okr_router
from .personas import router as personas_router
from .research import router as research_router
from .strategy import router as strategy_router

__all__ = [
    "personas_router",
    "competitors_router",
    "strategy_router",
    "calendar_router",
    "okr_router",
    "research_router",
]
