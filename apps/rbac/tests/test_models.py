"""Tests for RBAC models: Role, Permission, RoleAssignment, PermissionAssignment, Workspace."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.rbac.models import Permission, PermissionAssignment, Role, RoleAssignment, Workspace

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tenant_id() -> str:
    """Return a consistent tenant ID for tests."""
    return "test-tenant-001"


@pytest.fixture
def role(tenant_id: str) -> Role:
    """Create and return a basic Role instance."""
    return Role.objects.create(
        name="Test Role",
        description="A test role",
        permissions=["content:read", "content:write"],
        tenant_id=tenant_id,
    )


@pytest.fixture
def parent_role(tenant_id: str) -> Role:
    """Create and return a parent Role with base permissions."""
    return Role.objects.create(
        name="Parent Role",
        description="Parent role with inherited permissions",
        permissions=["admin:read"],
        tenant_id=tenant_id,
    )


@pytest.fixture
def permission(tenant_id: str) -> Permission:
    """Create and return a Permission instance."""
    return Permission.objects.create(
        codename="content_creation:write",
        name="Create Content",
        module="content_creation",
        action="write",
        description="Allows creating content",
    )


@pytest.fixture
def role_assignment(role: Role, tenant_id: str) -> RoleAssignment:
    """Create and return a RoleAssignment instance."""
    return RoleAssignment.objects.create(
        user_id="user-001",
        role=role,
        tenant_id=tenant_id,
        workspace_id="",
        granted_by="admin-001",
    )


# ---------------------------------------------------------------------------
# Role tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_role_creation(role: Role) -> None:
    """Role can be created with basic fields."""
    assert role.id is not None
    assert role.name == "Test Role"
    assert role.description == "A test role"
    assert role.permissions == ["content:read", "content:write"]
    assert role.tenant_id == "test-tenant-001"
    assert role.is_system is False
    assert role.created_at is not None
    assert role.updated_at is not None


@pytest.mark.django_db
def test_role_str(role: Role) -> None:
    """Role string representation returns the name."""
    assert str(role) == "Test Role"


@pytest.mark.django_db
def test_role_permission_inheritance(parent_role: Role, tenant_id: str) -> None:
    """Child role inherits permissions from parent via get_all_permissions."""
    child = Role.objects.create(
        name="Child Role",
        permissions=["content:read"],
        tenant_id=tenant_id,
        parent=parent_role,
    )
    all_perms = child.get_all_permissions()
    assert "content:read" in all_perms
    assert "admin:read" in all_perms
    assert sorted(all_perms) == ["admin:read", "content:read"]


@pytest.mark.django_db
def test_role_has_permission_direct(role: Role) -> None:
    """has_permission returns True for directly assigned permission."""
    assert role.has_permission("content:read") is True


@pytest.mark.django_db
def test_role_has_permission_inherited(parent_role: Role, tenant_id: str) -> None:
    """has_permission returns True for inherited permission."""
    child = Role.objects.create(
        name="Child Role",
        permissions=["content:read"],
        tenant_id=tenant_id,
        parent=parent_role,
    )
    assert child.has_permission("admin:read") is True


@pytest.mark.django_db
def test_role_has_permission_missing(role: Role) -> None:
    """has_permission returns False for unknown permission."""
    assert role.has_permission("admin:delete") is False


@pytest.mark.django_db
def test_role_unique_name_per_tenant(tenant_id: str) -> None:
    """Duplicate role name within same tenant raises IntegrityError."""
    Role.objects.create(name="Unique Role", tenant_id=tenant_id)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Role.objects.create(name="Unique Role", tenant_id=tenant_id)


@pytest.mark.django_db
def test_role_unique_constraint_different_tenants(tenant_id: str) -> None:
    """Same role name in different tenants is allowed."""
    Role.objects.create(name="Shared Role", tenant_id=tenant_id)
    role2 = Role.objects.create(name="Shared Role", tenant_id="other-tenant")
    assert role2.id is not None


# ---------------------------------------------------------------------------
# Permission tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_permission_creation(permission: Permission) -> None:
    """Permission can be created with all required fields."""
    assert permission.id is not None
    assert permission.codename == "content_creation:write"
    assert permission.name == "Create Content"
    assert permission.module == "content_creation"
    assert permission.action == "write"


@pytest.mark.django_db
def test_permission_str(permission: Permission) -> None:
    """Permission string representation includes codename and name."""
    assert str(permission) == "content_creation:write (Create Content)"


@pytest.mark.django_db
def test_permission_unique_codename() -> None:
    """Duplicate codename raises IntegrityError."""
    Permission.objects.create(
        codename="unique:action",
        name="Unique Action",
        module="unique",
        action="action",
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Permission.objects.create(
                codename="unique:action",
                name="Duplicate",
                module="unique",
                action="action",
            )


@pytest.mark.django_db
def test_permission_ordering() -> None:
    """Permissions are ordered by module then codename."""
    Permission.objects.create(codename="b:write", name="B Write", module="b", action="write")
    Permission.objects.create(codename="a:read", name="A Read", module="a", action="read")
    perms = list(Permission.objects.all())
    assert perms[0].module == "a"
    assert perms[1].module == "b"


# ---------------------------------------------------------------------------
# RoleAssignment tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_role_assignment_creation(role_assignment: RoleAssignment) -> None:
    """RoleAssignment can be created with required fields."""
    assert role_assignment.id is not None
    assert role_assignment.user_id == "user-001"
    assert role_assignment.role.name == "Test Role"
    assert role_assignment.tenant_id == "test-tenant-001"
    assert role_assignment.granted_by == "admin-001"


@pytest.mark.django_db
def test_role_assignment_str(role_assignment: RoleAssignment) -> None:
    """String representation includes user, role and tenant."""
    assert str(role_assignment) == "user-001 -> Test Role @ test-tenant-001"


@pytest.mark.django_db
def test_role_assignment_str_with_workspace(
    role: Role,
    tenant_id: str,
) -> None:
    """String representation includes workspace when set."""
    assignment = RoleAssignment.objects.create(
        user_id="user-002",
        role=role,
        tenant_id=tenant_id,
        workspace_id="ws-001",
        granted_by="admin-001",
    )
    assert str(assignment) == "user-002 -> Test Role @ test-tenant-001/ws-001"


@pytest.mark.django_db
def test_role_assignment_is_expired_false(role_assignment: RoleAssignment) -> None:
    """is_expired returns False when expires_at is None."""
    assert role_assignment.is_expired() is False


@pytest.mark.django_db
def test_role_assignment_is_expired_true(
    role: Role,
    tenant_id: str,
) -> None:
    """is_expired returns True when expires_at is in the past."""
    past = timezone.now() - timedelta(hours=1)
    assignment = RoleAssignment.objects.create(
        user_id="user-003",
        role=role,
        tenant_id=tenant_id,
        granted_by="admin-001",
        expires_at=past,
    )
    assert assignment.is_expired() is True


@pytest.mark.django_db
def test_role_assignment_is_expired_future(
    role: Role,
    tenant_id: str,
) -> None:
    """is_expired returns False when expires_at is in the future."""
    future = timezone.now() + timedelta(hours=1)
    assignment = RoleAssignment.objects.create(
        user_id="user-004",
        role=role,
        tenant_id=tenant_id,
        granted_by="admin-001",
        expires_at=future,
    )
    assert assignment.is_expired() is False


@pytest.mark.django_db
def test_role_assignment_unique_together(
    role: Role,
    tenant_id: str,
) -> None:
    """Duplicate user/role/tenant/workspace raises IntegrityError."""
    RoleAssignment.objects.create(
        user_id="dup-user",
        role=role,
        tenant_id=tenant_id,
        workspace_id="ws-dup",
        granted_by="admin-001",
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            RoleAssignment.objects.create(
                user_id="dup-user",
                role=role,
                tenant_id=tenant_id,
                workspace_id="ws-dup",
                granted_by="admin-002",
            )


# ---------------------------------------------------------------------------
# PermissionAssignment tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_permission_assignment_creation(
    role: Role,
    permission: Permission,
) -> None:
    """PermissionAssignment can be created linking role to permission."""
    pa = PermissionAssignment.objects.create(
        role=role,
        permission=permission,
        conditions={"status": "draft"},
    )
    assert pa.id is not None
    assert pa.role == role
    assert pa.permission == permission
    assert pa.conditions == {"status": "draft"}


@pytest.mark.django_db
def test_permission_assignment_str(role: Role, permission: Permission) -> None:
    """String representation shows role to permission mapping."""
    pa = PermissionAssignment.objects.create(role=role, permission=permission)
    assert str(pa) == "Test Role -> content_creation:write"


@pytest.mark.django_db
def test_permission_assignment_unique_together(
    role: Role,
    permission: Permission,
) -> None:
    """Duplicate role+permission raises IntegrityError."""
    PermissionAssignment.objects.create(role=role, permission=permission)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            PermissionAssignment.objects.create(role=role, permission=permission)


# ---------------------------------------------------------------------------
# Workspace tests
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace(tenant_id: str) -> Workspace:
    """Create and return a Workspace instance."""
    return Workspace.objects.create(
        name="Test Workspace",
        slug="test-workspace",
        tenant_id=tenant_id,
        description="A test workspace",
        settings={"theme": "dark"},
        is_active=True,
    )


@pytest.mark.django_db
def test_workspace_creation(workspace: Workspace) -> None:
    """Workspace can be created with all fields."""
    assert workspace.id is not None
    assert workspace.name == "Test Workspace"
    assert workspace.slug == "test-workspace"
    assert workspace.tenant_id == "test-tenant-001"
    assert workspace.description == "A test workspace"
    assert workspace.settings == {"theme": "dark"}
    assert workspace.is_active is True


@pytest.mark.django_db
def test_workspace_str(workspace: Workspace) -> None:
    """String representation includes name and slug."""
    assert str(workspace) == "Test Workspace (test-workspace)"


@pytest.mark.django_db
def test_workspace_unique_slug_per_tenant(tenant_id: str) -> None:
    """Duplicate slug within same tenant raises IntegrityError."""
    Workspace.objects.create(name="WS1", slug="unique-slug", tenant_id=tenant_id)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Workspace.objects.create(name="WS2", slug="unique-slug", tenant_id=tenant_id)


@pytest.mark.django_db
def test_workspace_slug_unique_globally() -> None:
    """Slug must be globally unique across tenants."""
    Workspace.objects.create(name="WS1", slug="global-slug", tenant_id="tenant-a")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Workspace.objects.create(name="WS2", slug="global-slug", tenant_id="tenant-b")
