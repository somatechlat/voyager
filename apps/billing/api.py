"""Billing API.

Endpoints for billing and subscription management — invoicing,
plan management, usage tracking, payment processing, reporting.

Aggregates all billing sub-routers under the /billing path:
  /billing/time-entries     → Time tracking
  /billing/budgets          → Project budgets
  /billing/invoices         → Invoice generation & management
  /billing/expenses         → Expense tracking
  /billing/profitability    → P&L analysis
  /billing/retainers        → Retainer management
  /billing/payments         → Payment processing
"""

from __future__ import annotations

from ninja import Router

from apps.billing.views import (
    budgets_router,
    expenses_router,
    invoices_router,
    payments_router,
    profitability_router,
    retainers_router,
    time_entries_router,
)
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())

# Register all billing sub-routers
router.add_router("/time-entries", time_entries_router, tags=["Billing"])
router.add_router("/budgets", budgets_router, tags=["Billing"])
router.add_router("/invoices", invoices_router, tags=["Billing"])
router.add_router("/expenses", expenses_router, tags=["Billing"])
router.add_router("/profitability", profitability_router, tags=["Billing"])
router.add_router("/retainers", retainers_router, tags=["Billing"])
router.add_router("/payments", payments_router, tags=["Billing"])


@router.get("/health", tags=["Billing"])
def module_health(request):
    """Billing module health check."""
    return {"status": "ok", "module": "billing"}
