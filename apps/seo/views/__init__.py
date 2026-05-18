"""SEO views package.

Exports all Ninja view endpoints for the SEO module.
"""

from __future__ import annotations

from apps.seo.views.backlinks import router as backlinks_router
from apps.seo.views.content import router as content_router
from apps.seo.views.keywords import router as keywords_router
from apps.seo.views.onpage import router as onpage_router
from apps.seo.views.rank import router as rank_router
from apps.seo.views.reports import router as reports_router
from apps.seo.views.technical import router as technical_router

__all__ = [
    "backlinks_router",
    "content_router",
    "keywords_router",
    "onpage_router",
    "rank_router",
    "reports_router",
    "technical_router",
]
