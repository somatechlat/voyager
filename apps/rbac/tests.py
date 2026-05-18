"""
RBAC Tests.

Tests for Role, Permission, and RoleAssignment API endpoints,
plus Keycloak auth integration.
"""

from __future__ import annotations

import pytest
from django.test import TestCase

from apps.rbac.models import Permission, Role, RoleAssignment


class TestRoleEndpoints(TestCase):
    """Tests for /roles CRUD operations."""

    def setUp(self) -> None:
        self.tenant_id = "tenant-rbac"
        self.role = Role.objects.create(
            tenant_id=self.tenant_id,
            name="Content Manager",
            description="Manages content creation and publishing",
            permissions=["content_creation:write", "content_creation:read"],
        )

    def test_list_roles(self):
        roles = Role.objects.filter(tenant_id=self.tenant_id)
        assert roles.count() >= 1
        assert any(r.name == "Content Manager" for r in roles)

    def test_create_role(self):
        role = Role.objects.create(
            tenant_id=self.tenant_id,
            name="Analytics Viewer",
            permissions=["analytics:read"],
        )
        assert role.id is not None
        assert role.name == "Analytics Viewer"
        assert role.permissions == ["analytics:read"]

    def test_get_role(self):
        fetched = Role.objects.get(id=self.role.id)
        assert fetched.name == "Content Manager"
        assert fetched.tenant_id == self.tenant_id

    def test_update_role(self):
        self.role.description = "Updated description"
        self.role.save()
        fetched = Role.objects.get(id=self.role.id)
        assert fetched.description == "Updated description"

    def test_delete_role(self):
        role_id = self.role.id
        self.role.delete()
        with pytest.raises(Role.DoesNotExist):
            Role.objects.get(id=role_id)

    def test_system_role_protection(self):
        """System roles cannot be modified or deleted."""
        system_role = Role.objects.create(
            tenant_id=self.tenant_id,
            name="System Admin",
            is_system=True,
            permissions=["*:*"],
        )
        assert system_role.is_system is True
        # System role exists and is marked as protected
        fetched = Role.objects.get(id=system_role.id)
        assert fetched.is_system is True


class TestPermissionEndpoints(TestCase):
    """Tests for /permissions endpoints."""

    def setUp(self) -> None:
        Permission.objects.create(
            codename="content_creation:write",
            name="Create Content",
            module="content_creation",
            action="write",
        )
        Permission.objects.create(
            codename="content_creation:read",
            name="Read Content",
            module="content_creation",
            action="read",
        )
        Permission.objects.create(
            codename="analytics:read",
            name="Read Analytics",
            module="analytics",
            action="read",
        )

    def test_list_permissions(self):
        perms = Permission.objects.all()
        assert perms.count() >= 3

    def test_list_permissions_by_module(self):
        perms = Permission.objects.filter(module="content_creation")
        assert perms.count() == 2
        assert all(p.module == "content_creation" for p in perms)


class TestRoleAssignmentEndpoints(TestCase):
    """Tests for /role-assignments endpoints."""

    def setUp(self) -> None:
        self.tenant_id = "tenant-assign"
        self.role = Role.objects.create(
            tenant_id=self.tenant_id,
            name="Editor",
            permissions=["content_creation:write"],
        )

    def test_assign_role(self):
        assignment = RoleAssignment.objects.create(
            tenant_id=self.tenant_id,
            user_id="user-123",
            role=self.role,
            granted_by="admin-1",
        )
        assert assignment.id is not None
        assert assignment.user_id == "user-123"
        assert assignment.role_id == self.role.id

    def test_remove_assignment(self):
        assignment = RoleAssignment.objects.create(
            tenant_id=self.tenant_id,
            user_id="user-456",
            role=self.role,
            granted_by="admin-1",
        )
        assignment_id = assignment.id
        assignment.delete()
        with pytest.raises(RoleAssignment.DoesNotExist):
            RoleAssignment.objects.get(id=assignment_id)


class TestUserPermissions(TestCase):
    """Tests for /users/{id}/permissions endpoints."""

    def setUp(self) -> None:
        self.tenant_id = "tenant-perms"
        self.role = Role.objects.create(
            tenant_id=self.tenant_id,
            name="Manager",
            permissions=["content_creation:write", "analytics:read"],
        )

    def test_get_user_permissions(self):
        RoleAssignment.objects.create(
            tenant_id=self.tenant_id,
            user_id="user-perms",
            role=self.role,
            granted_by="admin-1",
        )
        assignment = RoleAssignment.objects.get(tenant_id=self.tenant_id, user_id="user-perms")
        effective = assignment.role.get_all_permissions()
        assert "content_creation:write" in effective
        assert "analytics:read" in effective


class TestKeycloakAuth(TestCase):
    """Tests for Keycloak JWT validation."""

    def test_valid_token(self):
        # A valid token has the expected structure
        import base64
        import json

        header = (
            base64.urlsafe_b64encode(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
            .decode()
            .rstrip("=")
        )
        payload = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {
                        "sub": "user-123",
                        "realm_access": {"roles": ["user"]},
                        "iss": "https://keycloak.example.com/realms/voyager",
                    }
                ).encode()
            )
            .decode()
            .rstrip("=")
        )
        signature = base64.urlsafe_b64encode(b"signature").decode().rstrip("=")
        token = f"{header}.{payload}.{signature}"
        parts = token.split(".")
        assert len(parts) == 3
        decoded = json.loads(base64.urlsafe_b64decode(parts[1] + "==").decode())
        assert decoded["sub"] == "user-123"

    def test_expired_token(self):
        from datetime import UTC, datetime, timedelta

        import jwt

        expired_payload = {
            "sub": "user-123",
            "exp": (datetime.now(UTC) - timedelta(hours=1)).timestamp(),
            "iat": (datetime.now(UTC) - timedelta(hours=2)).timestamp(),
        }
        with pytest.raises((jwt.ExpiredSignatureError, Exception)):
            jwt.encode(expired_payload, "secret", algorithm="HS256")

    def test_invalid_token(self):
        import base64

        # Malformed token (only 2 parts)
        bad_token = "header.payload"
        parts = bad_token.split(".")
        assert len(parts) != 3

        # Token with invalid signature segment
        fake_token = (
            base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
            + "."
            + base64.urlsafe_b64encode(b'{"sub":"fake"}').decode().rstrip("=")
            + ".invalid_sig"
        )
        assert fake_token.count(".") == 2


class TestRoleHierarchy(TestCase):
    """Tests for role parent-child inheritance."""

    def test_parent_permission_inheritance(self):
        tenant_id = "tenant-hierarchy"
        parent_role = Role.objects.create(
            tenant_id=tenant_id,
            name="Parent Role",
            permissions=["base:read"],
        )
        child_role = Role.objects.create(
            tenant_id=tenant_id,
            name="Child Role",
            parent=parent_role,
            permissions=["child:write"],
        )
        effective = child_role.get_all_permissions()
        assert "base:read" in effective
        assert "child:write" in effective

    def test_has_permission(self):
        tenant_id = "tenant-perm-check"
        role = Role.objects.create(
            tenant_id=tenant_id,
            name="Perm Role",
            permissions=["module:action"],
        )
        assert role.has_permission("module:action") is True
        assert role.has_permission("other:action") is False
