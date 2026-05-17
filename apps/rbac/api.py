"""RBAC API endpoints for Voyager (backward-compatible re-export).

This module re-exports the router from ``apps.rbac.views`` for backward
compatibility. Use ``from apps.rbac.views import router`` in new code.
"""

from apps.rbac.views import router  # noqa: F401
