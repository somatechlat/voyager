"""API tests for Team endpoints.

Tests tasks, channels, activity under ``/api/v1/team/``.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.team.models.tasks import Task, TaskComment
from apps.team.models.messaging import MessageChannel
from apps.team.models.activity import ActivityFeed

client = Client()


@pytest.fixture
def task(tenant_id: str) -> Task:
    """Create a test task."""
    return Task.objects.create(
        tenant_id=tenant_id,
        title="Test Task",
        description="A task for API testing",
        status="todo",
        priority="high",
        assignee_id="user-001",
        creator_id="user-002",
    )


@pytest.fixture
def channel(tenant_id: str) -> MessageChannel:
    """Create a test message channel."""
    return MessageChannel.objects.create(
        tenant_id=tenant_id,
        name="general",
        channel_type="public",
        description="General discussion",
    )


@pytest.fixture
def activity(tenant_id: str) -> ActivityFeed:
    """Create a test activity feed entry."""
    return ActivityFeed.objects.create(
        tenant_id=tenant_id,
        user_id="user-001",
        action="task_created",
        entity_type="task",
        entity_id="task-001",
        details={"title": "Test Task"},
    )


@pytest.mark.django_db
def test_team_health_requires_auth() -> None:
    """GET /team/health without auth returns 401."""
    response = client.get("/api/v1/team/health")
    assert response.status_code == 401


@pytest.mark.django_db
def test_team_health(auth_headers: dict[str, str]) -> None:
    """GET /team/health returns module health."""
    response = client.get("/api/v1/team/health", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["module"] == "team"


@pytest.mark.django_db
def test_list_tasks(auth_headers: dict[str, str], task: Task) -> None:
    """GET /team/tasks returns tasks."""
    response = client.get("/api/v1/team/tasks", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_task(auth_headers: dict[str, str]) -> None:
    """POST /team/tasks creates a task."""
    payload = {
        "title": "API Task",
        "description": "Created via API",
        "status": "todo",
        "priority": "medium",
        "assignee_id": "user-003",
    }
    response = client.post(
        "/api/v1/team/tasks",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "API Task"


@pytest.mark.django_db
def test_get_task(auth_headers: dict[str, str], task: Task) -> None:
    """GET /team/tasks/{id} returns a task."""
    response = client.get(f"/api/v1/team/tasks/{task.id}", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Task"


@pytest.mark.django_db
def test_update_task(auth_headers: dict[str, str], task: Task) -> None:
    """PUT /team/tasks/{id} updates a task."""
    payload = {"title": "Updated Task", "status": "in_progress"}
    response = client.put(
        f"/api/v1/team/tasks/{task.id}",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Task"


@pytest.mark.django_db
def test_delete_task(auth_headers: dict[str, str], task: Task) -> None:
    """DELETE /team/tasks/{id} removes a task."""
    response = client.delete(f"/api/v1/team/tasks/{task.id}", **auth_headers)
    assert response.status_code == 200
    assert not Task.objects.filter(id=task.id).exists()


@pytest.mark.django_db
def test_list_channels(auth_headers: dict[str, str], channel: MessageChannel) -> None:
    """GET /team/channels returns message channels."""
    response = client.get("/api/v1/team/channels", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.django_db
def test_create_channel(auth_headers: dict[str, str]) -> None:
    """POST /team/channels creates a channel."""
    payload = {
        "name": "api-channel",
        "channel_type": "private",
        "description": "Channel for API tests",
    }
    response = client.post(
        "/api/v1/team/channels",
        payload,
        content_type="application/json",
        **auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "api-channel"


@pytest.mark.django_db
def test_list_activity(auth_headers: dict[str, str], activity: ActivityFeed) -> None:
    """GET /team/activity returns activity feed entries."""
    response = client.get("/api/v1/team/activity", **auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
