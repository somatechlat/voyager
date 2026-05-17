"""
Voyager API — Main Router Registry.

Follows Voyant's api.py pattern exactly:
  - NinjaAPI instance with unique namespace for pytest collision avoidance
  - All 19 module routers imported and registered with tags
  - Version 1.0.0, Voyager branding

Module Router Registry:
    /rbac          → RBAC (roles, permissions, assignments)
    /audit         → Audit logs (query, export)
    /content       → Content Creation
    /publish       → Publishing
    /campaigns     → Campaigns
    /strategy      → Strategy
    /analytics     → Analytics v2
    /scraping      → Web Scraping v2
    /agents        → AI Agents
    /social        → Social Media
    /seo           → SEO
    /email         → Email Marketing
    /clients       → Clients
    /billing       → Billing
    /assets        → Assets
    /team          → Team
    /workflows     → Workflows v2
    /integrations  → Integrations
    /governance    → Governance v2
"""

from __future__ import annotations

import sys
import uuid

from ninja import NinjaAPI

from apps.ai_agents.api import router as agents_router
from apps.analytics_v2.api import router as analytics_router
from apps.assets.api import router as assets_router
from apps.audit.api import router as audit_router
from apps.billing.api import router as billing_router
from apps.campaigns.api import router as campaigns_router
from apps.clients.api import router as clients_router
from apps.content_creation.api import router as content_router
from apps.email_marketing.api import router as email_router
from apps.governance_v2.api import router as governance_router
from apps.integrations.api import router as integrations_router
from apps.publishing.api import router as publishing_router

# Import all module routers
from apps.rbac.api import router as rbac_router
from apps.seo.api import router as seo_router
from apps.social_media.api import router as social_router
from apps.strategy.api import router as strategy_router
from apps.team.api import router as team_router
from apps.web_scraping_v2.api import router as scraping_router
from apps.workflows_v2.api import router as workflows_router

# Same pytest collision avoidance as Voyant
urls_namespace = "voyager_v1"
if "pytest" in sys.modules:
    try:
        NinjaAPI._registry.clear()
    except Exception:
        pass
    urls_namespace = f"voyager_v1_{uuid.uuid4().hex}"

voyager_api = NinjaAPI(
    title="Voyager API",
    description="Enterprise Marketing Automation Platform",
    version="1.0.0",
    urls_namespace=urls_namespace,
)

# Register all 19 module routers
voyager_api.add_router("/rbac", rbac_router, tags=["RBAC"])
voyager_api.add_router("/audit", audit_router, tags=["Audit"])
voyager_api.add_router("/content", content_router, tags=["Content Creation"])
voyager_api.add_router("/publish", publishing_router, tags=["Publishing"])
voyager_api.add_router("/campaigns", campaigns_router, tags=["Campaigns"])
voyager_api.add_router("/strategy", strategy_router, tags=["Strategy"])
voyager_api.add_router("/analytics", analytics_router, tags=["Analytics"])
voyager_api.add_router("/scraping", scraping_router, tags=["Web Scraping"])
voyager_api.add_router("/agents", agents_router, tags=["AI Agents"])
voyager_api.add_router("/social", social_router, tags=["Social Media"])
voyager_api.add_router("/seo", seo_router, tags=["SEO"])
voyager_api.add_router("/email", email_router, tags=["Email Marketing"])
voyager_api.add_router("/clients", clients_router, tags=["Clients"])
voyager_api.add_router("/billing", billing_router, tags=["Billing"])
voyager_api.add_router("/assets", assets_router, tags=["Assets"])
voyager_api.add_router("/team", team_router, tags=["Team"])
voyager_api.add_router("/workflows", workflows_router, tags=["Workflows"])
voyager_api.add_router("/integrations", integrations_router, tags=["Integrations"])
voyager_api.add_router("/governance", governance_router, tags=["Governance"])
