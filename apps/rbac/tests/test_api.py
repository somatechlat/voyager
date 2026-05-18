"""API tests for RBAC endpoints — roles, permissions, assignments, workspaces.

Tests GET / POST / PUT / DELETE for all RBAC router endpoints mounted under
``/api/v1/rbac/``.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.rbac.models import Permission, Role, RoleAssignment, Workspace

client = Client()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def role(tenant_id: str) -> Role:
    """Create a test role."""
    return Role.objects.create(
        name="Test Role",
        description="A role for API testing",
        permissions=["content:read", "content:write"],
        tenant_id=tenant_id,
    )


@pytest.fixture
def permission() -> Permission:
    """Create a test permission."""
    return Permission.objects.create(
        codename="test:read",
        name="Test Read",
        module="test",
        action="read",
        description="Permission for testing",
    )


@pytest.fixture
def workspace(tenant_id: str) -> Workspace:
    """Create a test workspace."""
    return Workspace.objects.create(
        name="Test Workspace",
        slug="test-workspace",
        tenant_id=tenant_id,
        description="Workspace for API testing",
    )


# ---------------------------------------------------------------------------
# Role endpoints
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_list_roles_requires_auth() -> None:
    """GET /rbac/roles without auth returns 401."""
    response = client.get("/api/v1/rbac/roles")
    assert response.status_code == 401


@pytest.mark.django_db
def test_list_roles(auth_headers: dict[str, str]) -> None:
    """GET /rbac/roles returns a paginated list of roles."""
    Role.objects.create(name="Role A", tenant_id="test-tenant-001")
    Role.objects.create(name="Role B", tenant_id="test-tenant-001")

    response = client.get("/api/v1/rbac/roles", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 2


@pytest.mark.django_db
def test_create_role(auth_headers: dict[str, str]) -> None:
    """POST /rbac/roles creates a new role."""
    payload = {
        "name": "API Test Role",
        "description": "Created via API test",
        "permissions": ["read:campaigns", "write:campaigns"],
    }
    response = client.post(
        "/api/v1/rbac/roles",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "API Test Role"
    assert "id" in data


@pytest.mark.django_db
def test_get_role(auth_headers: dict[str, str], role: Role) -> None:
    """GET /rbac/roles/{role_id} returns a single role."""
    response = client.get(f"/api/v1/rbac/roles/{role.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["role"]["name"] == "Test Role"


@pytest.mark.django_db
def test_get_role_not_found(auth_headers: dict[str, str]) -> None:
    """GET /rbac/roles/{role_id} with invalid ID returns 404."""
    response = client.get("/api/v1/rbac/roles/999999", **auth_headers)
    assert response.status_code in (404, 400)


@pytest.mark.django_db
def test_update_role(auth_headers: dict[str, str], role: Role) -> None:
    """PUT /rbac/roles/{role_id} updates a role."""
    payload = {
        "name": "Updated Role",
        "description": "Updated description",
        "permissions": ["new:perm"],
    }
    response = client.put(
        f"/api/v1/rbac/roles/{role.id}",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Role"


@pytest.mark.django_db
def test_delete_role(auth_headers: dict[str, str], role: Role) -> None:
    """DELETE /rbac/roles/{role_id} removes a non-system role."""
    response = client.delete(f"/api/v1/rbac/roles/{role.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "deleted"
    assert not Role.objects.filter(id=role.id).exists()


# ---------------------------------------------------------------------------
# Permission endpoints
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_list_permissions(auth_headers: dict[str, str], permission: Permission) -> None:
    """GET /rbac/permissions returns all permissions."""
    response = client.get("/api/v1/rbac/permissions", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.django_db
def test_list_permissions_filtered(auth_headers: dict[str, str]) -> None:
    """GET /rbac/permissions?module=X filters by module."""
    Permission.objects.create(codename="mod1:read", name="R1", module="mod1", action="read")
    Permission.objects.create(codename="mod2:read", name="R2", module="mod2", action="read")
    response = client.get("/api/v1/rbac/permissions?module=mod1", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert all(p["module"] == "mod1" for p in data["items"])


# ---------------------------------------------------------------------------
# Assignment endpoints
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_list_role_assignments(auth_headers: dict[str, str], role: Role) -> None:
    """GET /rbac/role-assignments returns a list of assignments."""
    RoleAssignment.objects.create(user_id="user-001", role=role, tenant_id="test-tenant-001")
    response = client.get("/api/v1/rbac/role-assignments", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.django_db
def test_assign_role(auth_headers: dict[str, str], role: Role) -> None:
    """POST /rbac/role-assignments creates an assignment."""
    payload = {"user_id": "user-002", "role_id": role.id, "tenant_id": "test-tenant-001"}
    response = client.post(
        "/api/v1/rbac/role-assignments",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_revoke_role_assignment(auth_headers: dict[str, str], role: Role) -> None:
    """DELETE /rbac/role-assignments/{id} revokes an assignment."""
    assignment = RoleAssignment.objects.create(
        user_id="user-003", role=role, tenant_id="test-tenant-001"
    )
    response = client.delete(f"/api/v1/rbac/role-assignments/{assignment.id}", **auth_headers)
    assert response.status_code == 200
    assert not RoleAssignment.objects.filter(id=assignment.id).exists()


# ---------------------------------------------------------------------------
# Workspace endpoints
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_list_workspaces(auth_headers: dict[str, str], workspace: Workspace) -> None:
    """GET /rbac/workspaces returns a list of workspaces."""
    response = client.get("/api/v1/rbac/workspaces", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


@pytest.mark.django_db
def test_create_workspace(auth_headers: dict[str, str]) -> None:
    """POST /rbac/workspaces creates a new workspace."""
    payload = {"name": "New Workspace", "slug": "new-workspace", "tenant_id": "test-tenant-001"}
    response = client.post(
        "/api/v1/rbac/workspaces",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Workspace"


@pytest.mark.django_db
def test_get_workspace(auth_headers: dict[str, str], workspace: Workspace) -> None:
    """GET /rbac/workspaces/{id} returns a single workspace."""
    response = client.get(f"/api/v1/rbac/workspaces/{workspace.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["workspace"]["name"] == "Test Workspace"


@pytest.mark.django_db
def test_update_workspace(auth_headers: dict[str, str], workspace: Workspace) -> None:
    """PUT /rbac/workspaces/{id} updates a workspace."""
    payload = {
        "name": "Updated Workspace",
        "slug": "updated-workspace",
        "tenant_id": "test-tenant-001",
    }
    response = client.put(
        f"/api/v1/rbac/workspaces/{workspace.id}",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_delete_workspace(auth_headers: dict[str, str], workspace: Workspace) -> None:
    """DELETE /rbac/workspaces/{id} removes a workspace."""
    response = client.delete(f"/api/v1/rbac/workspaces/{workspace.id}", **auth_headers)
    assert response.status_code == 200
    assert not Workspace.objects.filter(id=workspace.id).exists()
