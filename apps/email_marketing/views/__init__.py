"""Email Marketing views package.

Assembles all email marketing API routers.
"""

from apps.email_marketing.views.ab_tests import router as ab_tests_router
from apps.email_marketing.views.analytics import router as analytics_router
from apps.email_marketing.views.automation import router as automation_router
from apps.email_marketing.views.campaigns import router as campaigns_router
from apps.email_marketing.views.deliverability import router as deliverability_router
from apps.email_marketing.views.segments import router as segments_router
from apps.email_marketing.views.subscribers import router as subscribers_router
from apps.email_marketing.views.templates import router as templates_router

__all__ = [
    "templates_router",
    "campaigns_router",
    "automation_router",
    "segments_router",
    "deliverability_router",
    "ab_tests_router",
    "analytics_router",
    "subscribers_router",
]
