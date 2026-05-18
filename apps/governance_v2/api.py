"""Governance v2 API.

Endpoints for compliance and governance — brand safety scanning,
compliance rule management, GDPR consent and DSR handling,
approval workflows, and data residency. All endpoints are
registered in ``apps.governance_v2.views`` and re-exported here.
"""

from apps.governance_v2.views import router  # noqa: F401
