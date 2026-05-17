"""Audit Log API endpoints for Voyager (backward-compatible re-export).

This module re-exports the router from ``apps.audit.views`` for backward
compatibility. Use ``from apps.audit.views import router`` in new code.
"""

from apps.audit.views import router  # noqa: F401
