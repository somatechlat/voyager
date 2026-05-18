"""Abstract base models for Strategy module.

Re-exports UUIDModel, TimeStampedModel, and TenantModel from
apps.core.models so all strategy models use the canonical base classes.
"""

from __future__ import annotations

from apps.core.models import TenantModel  # noqa: F401
from apps.core.models import TimeStampedModel  # noqa: F401
from apps.core.models import UUIDModel  # noqa: F401
