"""Billing views package.

Exports module-level routers for each billing subdomain.
"""

from __future__ import annotations

from apps.billing.views.budgets import router as budgets_router  # noqa: F401
from apps.billing.views.expenses import router as expenses_router  # noqa: F401
from apps.billing.views.invoices import router as invoices_router  # noqa: F401
from apps.billing.views.payments import router as payments_router  # noqa: F401
from apps.billing.views.profitability import (  # noqa: F401
    router as profitability_router,
)
from apps.billing.views.retainers import router as retainers_router  # noqa: F401
from apps.billing.views.time_entries import (  # noqa: F401
    router as time_entries_router,
)
