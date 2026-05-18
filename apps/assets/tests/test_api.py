"""API tests for Assets endpoints.

Tests assets, folders, collections under ``/api/v1/assets/``.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.assets.models import Asset, AssetFolder, AssetCollection

client = Client()


@pytest.fixture
def asset_folder(tenant_id: str) -> AssetFolder:
    """Create a test asset folder."""
    return AssetFolder.objects.create(
        tenant_id=tenant_id,
        name="Test Folder",
        description="Folder for API tests",
        path="/test",
    )


@pytest.fixture
def asset(tenant_id: str, asset_folder: AssetFolder) -> Asset:
    """Create a test asset."""
    return Asset.objects.create(
        tenant_id=tenant_id,
        folder=asset_folder,
        name="hero-banner.jpg",
        file_type="image",
        file_size=1024000,
        mime_type="image/jpeg",
        url="https://cdn.example.com/hero.jpg",
        metadata={"width": 1920, "height": 1080},
    )


@pytest.fixture
def collection(tenant_id: str) -> AssetCollection:
    """Create a test collection."""
    return AssetCollection.objects.create(
        tenant_id=tenant_id,
        name="Summer Campaign",
        description="Assets for summer 2024",
    )


@pytest.mark.django_db
def test_assets_health_requires_auth() -> None:
    """GET /assets/health without auth returns 401."""
    response = client.get("/api/v1/assets/health")
    assert response.status_code == 401


@pytest.mark.django_db
def test_assets_health(auth_headers: dict[str, str]) -> None:
    """GET /assets/health returns module health."""
    response = client.get("/api/v1/assets/health", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["module"] == "assets"


@pytest.mark.django_db
def test_list_assets(auth_headers: dict[str, str], asset: Asset) -> None:
    """GET /assets/assets returns assets."""
    response = client.get("/api/v1/assets/assets", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_asset(auth_headers: dict[str, str], asset_folder: AssetFolder) -> None:
    """POST /assets/assets creates an asset."""
    payload = {
        "name": "logo.png",
        "file_type": "image",
        "file_size": 512000,
        "mime_type": "image/png",
        "url": "https://cdn.example.com/logo.png",
        "folder_id": str(asset_folder.id),
        "metadata": {},
    }
    response = client.post(
        "/api/v1/assets/assets",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "logo.png"


@pytest.mark.django_db
def test_get_asset(auth_headers: dict[str, str], asset: Asset) -> None:
    """GET /assets/assets/{id} returns an asset."""
    response = client.get(f"/api/v1/assets/assets/{asset.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "hero-banner.jpg"


@pytest.mark.django_db
def test_list_folders(auth_headers: dict[str, str], asset_folder: AssetFolder) -> None:
    """GET /assets/folders returns folders."""
    response = client.get("/api/v1/assets/folders", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_folder(auth_headers: dict[str, str]) -> None:
    """POST /assets/folders creates a folder."""
    payload = {"name": "API Folder", "description": "Created via API", "path": "/api"}
    response = client.post(
        "/api/v1/assets/folders",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "API Folder"


@pytest.mark.django_db
def test_list_collections(auth_headers: dict[str, str], collection: AssetCollection) -> None:
    """GET /assets/collections returns collections."""
    response = client.get("/api/v1/assets/collections", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_collection(auth_headers: dict[str, str]) -> None:
    """POST /assets/collections creates a collection."""
    payload = {"name": "API Collection", "description": "Created via API"}
    response = client.post(
        "/api/v1/assets/collections",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "API Collection"
