"""Publishing views package.

Re-exports all view routers for registration in api.py.
"""

from __future__ import annotations

from .approval import router as approval_router
from .bulk import router as bulk_router
from .calendar import router as calendar_router
from .posts import router as posts_router
from .queue import router as queue_router
from .schedule import router as schedule_router

__all__ = [
    "approval_router",
    "bulk_router",
    "calendar_router",
    "posts_router",
    "queue_router",
    "schedule_router",
]
