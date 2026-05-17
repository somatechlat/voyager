"""Shared in-memory stores and helpers for RBAC views."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from django.http import HttpRequest
from ninja.errors import HttpError

from apps.rbac.auth import VoyagerKeycloakAuth, VoyagerUser

logger = logging.getLogger(__name__)

_roles_db: dict[str, dict[str, Any]] = {}
_permissions_db: dict[str, dict[str, Any]] = {}
_assignments_db: dict[str, dict[str, Any]] = {}
_workspaces_db: dict[str, dict[str, Any]] = {}
_role_activity_db: list[dict[str, Any]] = []

# Seed system roles on module load
if not _roles_db:
    _auth_ref = VoyagerKeycloakAuth()
    for role_name in _auth_ref.list_defined_roles():
        role_id = str(uuid4())
        perms = _auth_ref.get_role_permissions(role_name)
        _roles_db[role_id] = {
            "id": UUID(role_id),
            "name": role_name,
            "description": f"System role: {role_name}",
            "parent_id": None,
            "permissions": perms,
            "is_system": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

# Seed permissions from role map
if not _permissions_db:
    all_perms = _auth_ref.list_defined_permissions()
    for perm_codename in all_perms:
        perm_id = str(uuid4())
        parts = perm_codename.split(":")
        module = parts[1] if len(parts) > 1 else "global"
        action = parts[2] if len(parts) > 2 else "*"
        _permissions_db[perm_id] = {
            "id": UUID(perm_id),
            "codename": perm_codename,
            "name": perm_codename.replace(":", " ").title(),
            "module": module,
            "action": action,
        }


def get_user(request: HttpRequest) -> VoyagerUser:
    """Safely extract VoyagerUser from request."""
    user = getattr(request, "auth", None)
    if user is None or not isinstance(user, VoyagerUser):
        raise HttpError(401, "Authentication required")
    return user


def audit_log(
    action: str,
    actor: VoyagerUser,
    role_name: str,
    target_user_id: str | None = None,
    workspace_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Log a role activity event."""
    event = {
        "id": uuid4(),
        "action": action,
        "actor_id": actor.user_id,
        "target_user_id": target_user_id,
        "role_name": role_name,
        "tenant_id": actor.tenant_id,
        "workspace_id": workspace_id,
        "timestamp": datetime.utcnow(),
        "details": details or {},
    }
    _role_activity_db.append(event)
    logger.info(
        "Role activity: %s by %s (role=%s, tenant=%s)",
        action,
        actor.username,
        role_name,
        actor.tenant_id,
    )
