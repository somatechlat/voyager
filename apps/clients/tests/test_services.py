"""Tests for clients services — client CRUD, projects, portals."""

from __future__ import annotations

import uuid

import pytest

from apps.clients.models import Client, ClientContact, ClientPortal
from apps.clients.services import clients as client_service
from apps.clients.services import portals as portal_service


@pytest.fixture
def tenant_id() -> str:
    return "test-tenant-clients"


@pytest.fixture
def create_client(tenant_id, db):
    def _create(**kwargs):
        slug = kwargs.get("slug") or f"client-{uuid.uuid4().hex[:8]}"
        defaults = {
            "tenant_id": tenant_id,
            "name": f"Test Client {uuid.uuid4().hex[:8]}",
            "slug": slug,
            "industry": "Technology",
            "website": "https://example.com",
            "contact_name": "Test Contact",
            "contact_email": "test@example.com",
            "status": Client.Status.ACTIVE,
            "tier": Client.Tier.PRO,
        }
        defaults.update(kwargs)
        return Client.objects.create(**defaults)

    return _create


@pytest.fixture
def create_contact(db):
    def _create(client, **kwargs):
        defaults = {
            "client": client,
            "name": f"Contact {uuid.uuid4().hex[:8]}",
            "email": f"contact-{uuid.uuid4().hex[:6]}@example.com",
            "phone": "+1234567890",
            "role": "Manager",
            "is_primary": True,
        }
        defaults.update(kwargs)
        return ClientContact.objects.create(**defaults)

    return _create


# ── Client CRUD Service Tests ─────────────────────────────────────


class TestClientService:
    def test_list_clients_returns_all(self, create_client):
        c1 = create_client(name="Client A")
        c2 = create_client(name="Client B")
        result = client_service.list_clients("test-tenant-clients")
        assert result["total"] >= 2
        ids = {c.id for c in result["results"]}
        assert c1.id in ids
        assert c2.id in ids

    def test_list_clients_status_filter(self, create_client):
        create_client(name="Active Client", status=Client.Status.ACTIVE)
        create_client(name="Paused Client", status=Client.Status.PAUSED)
        result = client_service.list_clients("test-tenant-clients", status=Client.Status.ACTIVE)
        assert all(c.status == Client.Status.ACTIVE for c in result["results"])

    def test_list_clients_tier_filter(self, create_client):
        create_client(name="Basic Client", tier=Client.Tier.BASIC)
        create_client(name="Enterprise Client", tier=Client.Tier.ENTERPRISE)
        result = client_service.list_clients("test-tenant-clients", tier=Client.Tier.ENTERPRISE)
        assert all(c.tier == Client.Tier.ENTERPRISE for c in result["results"])

    def test_get_client(self, create_client):
        c = create_client(name="Specific Client")
        result = client_service.get_client(c.id, "test-tenant-clients")
        assert result is not None
        assert result.name == "Specific Client"

    def test_get_client_not_found(self, tenant_id):
        result = client_service.get_client(99999, tenant_id)
        assert result is None

    def test_create_client(self, tenant_id, db):
        client = client_service.create_client(
            tenant_id=tenant_id,
            name="New Client",
            slug="new-client",
            industry="Healthcare",
            website="https://newclient.com",
            contact_name="Jane Doe",
            contact_email="jane@newclient.com",
            status=Client.Status.ACTIVE,
            tier=Client.Tier.PRO,
        )
        assert client is not None
        assert client.name == "New Client"
        assert Client.objects.filter(id=client.id).exists()

    def test_create_client_with_unique_slug(self, tenant_id, db):
        slug = f"unique-{uuid.uuid4().hex[:8]}"
        client = client_service.create_client(tenant_id=tenant_id, name="Unique", slug=slug)
        assert client.slug == slug

    def test_update_client(self, create_client):
        c = create_client(name="Old Name")
        updated = client_service.update_client(
            c.id, data={"name": "New Name", "industry": "Finance"}
        )
        assert updated.name == "New Name"
        assert updated.industry == "Finance"

    def test_delete_client(self, create_client):
        c = create_client(name="To Delete")
        client_service.delete_client(c.id)
        assert not Client.objects.filter(id=c.id).exists()

    def test_list_clients_empty_tenant(self, tenant_id):
        result = client_service.list_clients(tenant_id + "-none")
        assert result["total"] == 0
        assert result["results"] == []


# ── Project Service Tests ─────────────────────────────────────────


class TestProjectService:
    def test_list_projects(self, create_client, tenant_id, db):
        c = create_client()
        from apps.clients.models.project import Project

        p1 = Project.objects.create(
            tenant_id=tenant_id,
            client=c,
            name="Project Alpha",
            status="active",
        )
        p2 = Project.objects.create(
            tenant_id=tenant_id,
            client=c,
            name="Project Beta",
            status="active",
        )
        result = client_service.list_projects("test-tenant-clients")
        assert result["total"] >= 2
        ids = {p.id for p in result["results"]}
        assert p1.id in ids
        assert p2.id in ids

    def test_list_projects_client_filter(self, create_client, tenant_id, db):
        c1 = create_client(name="Client One")
        c2 = create_client(name="Client Two")
        from apps.clients.models.project import Project

        Project.objects.create(tenant_id=tenant_id, client=c1, name="P1", status="active")
        Project.objects.create(tenant_id=tenant_id, client=c2, name="P2", status="active")
        result = client_service.list_projects("test-tenant-clients", client_id=c1.id)
        assert result["total"] == 1
        assert result["results"][0].name == "P1"

    def test_get_project(self, create_client, tenant_id, db):
        c = create_client()
        from apps.clients.models.project import Project

        p = Project.objects.create(tenant_id=tenant_id, client=c, name="Get Me", status="active")
        result = client_service.get_project(p.id, tenant_id)
        assert result is not None
        assert result.name == "Get Me"

    def test_create_project(self, create_client, tenant_id, db):
        c = create_client()
        project = client_service.create_project(
            tenant_id=tenant_id,
            client_id=c.id,
            name="Brand New Project",
            description="Project description",
            status="active",
            budget=50000.0,
        )
        assert project is not None
        assert project.name == "Brand New Project"

    def test_update_project(self, create_client, tenant_id, db):
        c = create_client()
        from apps.clients.models.project import Project

        p = Project.objects.create(tenant_id=tenant_id, client=c, name="Old Proj", status="active")
        updated = client_service.update_project(p.id, data={"name": "Updated Proj"})
        assert updated.name == "Updated Proj"


# ── Portal Service Tests ──────────────────────────────────────────


class TestPortalService:
    def test_get_or_create_portal(self, create_client):
        c = create_client(name="Portal Client")
        portal = portal_service.PortalService.get_or_create(
            c.id, {"slug": "portal-client", "is_active": True}
        )
        assert portal is not None
        assert portal.client_id == c.id
        assert ClientPortal.objects.filter(id=portal.id).exists()

    def test_get_or_create_existing(self, create_client):
        c = create_client()
        p1 = portal_service.PortalService.get_or_create(c.id, {})
        p2 = portal_service.PortalService.get_or_create(c.id, {})
        assert p1.id == p2.id

    def test_get_by_client(self, create_client):
        c = create_client()
        portal_service.PortalService.get_or_create(c.id, {})
        result = portal_service.PortalService.get_by_client(c.id)
        assert result is not None
        assert result.client_id == c.id

    def test_get_by_client_not_found(self):
        from ninja.errors import HttpError

        with pytest.raises(HttpError):
            portal_service.PortalService.get_by_client(99999)

    def test_update_portal(self, create_client):
        c = create_client()
        portal = portal_service.PortalService.get_or_create(c.id, {})
        updated = portal_service.PortalService.update(
            portal, {"custom_domain": "portal.example.com", "is_active": False}
        )
        assert updated.custom_domain == "portal.example.com"
        assert updated.is_active is False

    def test_delete_portal(self, create_client):
        c = create_client()
        portal = portal_service.PortalService.get_or_create(c.id, {})
        portal_id = portal.id
        portal_service.PortalService.delete(portal)
        assert not ClientPortal.objects.filter(id=portal_id).exists()

    def test_update_branding(self, create_client):
        c = create_client()
        portal = portal_service.PortalService.get_or_create(c.id, {})
        updated = portal_service.PortalService.update_branding(
            portal, {"primaryColor": "#FF0000", "logo": "https://logo.png"}
        )
        assert updated.branding["primaryColor"] == "#FF0000"
        assert updated.branding["logo"] == "https://logo.png"

    def test_validate_custom_domain_valid(self, create_client):
        c = create_client()
        portal = portal_service.PortalService.get_or_create(
            c.id, {"custom_domain": "portal.example.com"}
        )
        result = portal_service.PortalService.validate_custom_domain(portal)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_validate_custom_domain_invalid_chars(self, create_client):
        c = create_client()
        portal = portal_service.PortalService.get_or_create(
            c.id, {"custom_domain": "portal @ example.com"}
        )
        result = portal_service.PortalService.validate_custom_domain(portal)
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_validate_custom_domain_empty(self, create_client):
        c = create_client()
        portal = portal_service.PortalService.get_or_create(c.id, {})
        result = portal_service.PortalService.validate_custom_domain(portal)
        assert result["valid"] is True
