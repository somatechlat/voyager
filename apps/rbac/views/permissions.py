"""Permission list endpoints."""

from __future__ import annotations

from django.http import HttpRequest
from ninja import Query
from ninja.errors import HttpError

from apps.rbac.serializers import (
    PermissionListResponse,
    PermissionSchema,
)

from .stores import _permissions_db, get_user


def list_permissions(
    request: HttpRequest,
    module: str | None = Query(None, description="Filter by module name"),
    action: str | None = Query(None, description="Filter by action type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PermissionListResponse:
    """List all permissions, optionally filtered by module or action.

    Args:
        request: HTTP request.
        module: Optional module filter (e.g. ``"content_creation"``).
        action: Optional action filter (e.g. ``"read"``).
        page: Page number.
        page_size: Items per page.

    Returns:
        Paginated permission list.
    """
    user = get_user(request)
    if not user.has_permission("voyager:read:*"):
        raise HttpError(403, "Permission denied")

    all_perms = list(_permissions_db.values())

    if module:
        all_perms = [p for p in all_perms if p["module"] == module]
    if action:
        all_perms = [p for p in all_perms if p["action"] == action]

    total = len(all_perms)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = all_perms[start:end]

    items = [
        PermissionSchema(
            id=p["id"],
            codename=p["codename"],
            name=p["name"],
            module=p["module"],
            action=p["action"],
        )
        for p in page_items
    ]

    return PermissionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
