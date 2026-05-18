"""Campaign views package.

Assembles all campaign management API routers.
"""

from apps.campaigns.views.ab_testing import router as ab_testing_router
from apps.campaigns.views.briefs import router as briefs_router
from apps.campaigns.views.budget import router as budget_router
from apps.campaigns.views.channels import router as channels_router
from apps.campaigns.views.crud import router as crud_router
from apps.campaigns.views.lifecycle import router as lifecycle_router
from apps.campaigns.views.performance import router as performance_router

__all__ = [
    "crud_router",
    "lifecycle_router",
    "budget_router",
    "ab_testing_router",
    "performance_router",
    "channels_router",
    "briefs_router",
]
