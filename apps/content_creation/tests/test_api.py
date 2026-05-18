"""API tests for Content Creation endpoints.

Tests generate, brand-kits, templates, ab-tests, and revisions under
``/api/v1/content/``.
"""

from __future__ import annotations

import uuid

import pytest
from django.test import Client

from apps.content_creation.models import ABTest, BrandKit, ContentTemplate

client = Client()


@pytest.fixture
def brand_kit(tenant_id: str) -> BrandKit:
    """Create a test brand kit."""
    return BrandKit.objects.create(
        tenant_id=tenant_id,
        name="Test Brand Kit",
        description="Brand kit for API tests",
        voice="professional",
        tone_rules={"formal": True},
        color_palette={"primary": "#000"},
    )


@pytest.fixture
def content_template(tenant_id: str) -> ContentTemplate:
    """Create a test content template."""
    return ContentTemplate.objects.create(
        tenant_id=tenant_id,
        name="Test Template",
        description="Template for API tests",
        category="social",
        content_type="text",
        body="Hello {{ name }}!",
        variables=["name"],
        default_values={"name": "World"},
    )


@pytest.fixture
def ab_test(tenant_id: str) -> ABTest:
    """Create a test A/B test."""
    return ABTest.objects.create(
        tenant_id=tenant_id,
        name="Test A/B Test",
        content_generation_id=uuid.uuid4(),
        variants=[
            {"name": "A", "content": "Version A"},
            {"name": "B", "content": "Version B"},
        ],
        sample_size=1000,
        winner_criteria="engagement",
    )


@pytest.mark.django_db
def test_content_health_requires_auth() -> None:
    """GET /content/health without auth returns 401."""
    response = client.get("/api/v1/content/health")
    assert response.status_code == 401


@pytest.mark.django_db
def test_content_health(auth_headers: dict[str, str]) -> None:
    """GET /content/health returns module health."""
    response = client.get("/api/v1/content/health", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["module"] == "content_creation"


@pytest.mark.django_db
def test_list_brand_kits(auth_headers: dict[str, str], brand_kit: BrandKit) -> None:
    """GET /content/brand-kits returns brand kits."""
    response = client.get("/api/v1/content/brand-kits", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["name"] == "Test Brand Kit"


@pytest.mark.django_db
def test_create_brand_kit(auth_headers: dict[str, str]) -> None:
    """POST /content/brand-kits creates a brand kit."""
    payload = {
        "name": "New Brand Kit",
        "description": "Created via API",
        "voice": "casual",
        "tone_rules": {"formal": False},
        "color_palette": {"primary": "#fff"},
        "logo_url": "",
        "font_preferences": {},
        "forbidden_words": [],
        "required_phrases": [],
        "competitor_list": [],
        "avoid_topics": [],
        "target_audience": "",
        "min_readability": 0,
        "min_compliance_score": 0,
    }
    response = client.post(
        "/api/v1/content/brand-kits",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Brand Kit"
    assert "id" in data


@pytest.mark.django_db
def test_get_brand_kit(auth_headers: dict[str, str], brand_kit: BrandKit) -> None:
    """GET /content/brand-kits/{kit_id} returns a single brand kit."""
    response = client.get(f"/api/v1/content/brand-kits/{brand_kit.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Brand Kit"


@pytest.mark.django_db
def test_update_brand_kit(auth_headers: dict[str, str], brand_kit: BrandKit) -> None:
    """PUT /content/brand-kits/{kit_id} updates a brand kit."""
    payload = {
        "name": "Updated Brand Kit",
        "description": "Updated via API",
        "voice": "professional",
        "tone_rules": {},
        "color_palette": {},
        "logo_url": "",
        "font_preferences": {},
        "forbidden_words": [],
        "required_phrases": [],
        "competitor_list": [],
        "avoid_topics": [],
        "target_audience": "",
        "min_readability": 0,
        "min_compliance_score": 0,
    }
    response = client.put(
        f"/api/v1/content/brand-kits/{brand_kit.id}",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Brand Kit"


@pytest.mark.django_db
def test_delete_brand_kit(auth_headers: dict[str, str], brand_kit: BrandKit) -> None:
    """DELETE /content/brand-kits/{kit_id} removes a brand kit."""
    response = client.delete(f"/api/v1/content/brand-kits/{brand_kit.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data.get("deleted") is True
    assert not BrandKit.objects.filter(id=brand_kit.id).exists()


@pytest.mark.django_db
def test_list_templates(auth_headers: dict[str, str], content_template: ContentTemplate) -> None:
    """GET /content/templates returns templates."""
    response = client.get("/api/v1/content/templates", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_template(auth_headers: dict[str, str]) -> None:
    """POST /content/templates creates a template."""
    payload = {
        "name": "API Test Template",
        "description": "Created via API",
        "category": "email",
        "content_type": "text",
        "body": "Dear {{ name }}, welcome!",
        "variables": ["name"],
        "default_values": {"name": "User"},
        "brand_kit_id": None,
    }
    response = client.post(
        "/api/v1/content/templates",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "API Test Template"


@pytest.mark.django_db
def test_get_template(auth_headers: dict[str, str], content_template: ContentTemplate) -> None:
    """GET /content/templates/{id} returns a template."""
    response = client.get(f"/api/v1/content/templates/{content_template.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Template"


@pytest.mark.django_db
def test_update_template(auth_headers: dict[str, str], content_template: ContentTemplate) -> None:
    """PUT /content/templates/{id} updates a template."""
    payload = {
        "name": "Updated Template",
        "description": "Updated via API",
        "category": "social",
        "content_type": "text",
        "body": "Hi {{ name }}!",
        "variables": ["name"],
        "default_values": {},
        "brand_kit_id": None,
    }
    response = client.put(
        f"/api/v1/content/templates/{content_template.id}",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Template"


@pytest.mark.django_db
def test_delete_template(auth_headers: dict[str, str], content_template: ContentTemplate) -> None:
    """DELETE /content/templates/{id} removes a template."""
    response = client.delete(f"/api/v1/content/templates/{content_template.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data.get("deleted") is True
    assert not ContentTemplate.objects.filter(id=content_template.id).exists()


@pytest.mark.django_db
def test_render_template(auth_headers: dict[str, str], content_template: ContentTemplate) -> None:
    """POST /content/templates/{id}/render renders a template."""
    payload = {"variables": {"name": "Alice"}, "platform": "twitter"}
    response = client.post(
        f"/api/v1/content/templates/{content_template.id}/render",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "rendered" in data
    assert "Hello Alice!" in data["rendered"]


@pytest.mark.django_db
def test_list_ab_tests(auth_headers: dict[str, str], ab_test: ABTest) -> None:
    """GET /content/ab-tests returns A/B tests."""
    response = client.get("/api/v1/content/ab-tests", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_ab_test(auth_headers: dict[str, str]) -> None:
    """POST /content/ab-tests creates an A/B test."""
    payload = {
        "name": "New A/B Test",
        "content_generation_id": str(uuid.uuid4()),
        "variants": [
            {"name": "Control", "content": "Control version"},
            {"name": "Variant", "content": "Variant version"},
        ],
        "sample_size": 500,
        "winner_criteria": "clicks",
    }
    response = client.post(
        "/api/v1/content/ab-tests",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_get_ab_test(auth_headers: dict[str, str], ab_test: ABTest) -> None:
    """GET /content/ab-tests/{id} returns an A/B test."""
    response = client.get(f"/api/v1/content/ab-tests/{ab_test.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test A/B Test"


@pytest.mark.django_db
def test_update_ab_test(auth_headers: dict[str, str], ab_test: ABTest) -> None:
    """PUT /content/ab-tests/{id} updates an A/B test."""
    payload = {
        "name": "Updated A/B Test",
        "content_generation_id": str(ab_test.content_generation_id),
        "variants": ab_test.variants,
        "sample_size": 2000,
        "winner_criteria": "engagement",
    }
    response = client.put(
        f"/api/v1/content/ab-tests/{ab_test.id}",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated A/B Test"


@pytest.mark.django_db
def test_delete_ab_test(auth_headers: dict[str, str], ab_test: ABTest) -> None:
    """DELETE /content/ab-tests/{id} removes an A/B test."""
    response = client.delete(f"/api/v1/content/ab-tests/{ab_test.id}", **auth_headers)
    assert response.status_code == 200
    assert not ABTest.objects.filter(id=ab_test.id).exists()
