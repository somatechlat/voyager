"""Tests for team services — tasks, messaging, workload."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.team.models import Message, Task, TaskComment
from apps.team.services import messaging as msg_service
from apps.team.services import task_core as task_service
from apps.team.services import workload as wl_service


@pytest.fixture
def tenant_id() -> str:
    return "test-tenant-team"


@pytest.fixture
def create_task(tenant_id, db):
    def _create(**kwargs):
        defaults = {
            "tenant_id": tenant_id,
            "title": f"Task {uuid.uuid4().hex[:8]}",
            "description": "Test task description",
            "assignee_id": "user-1",
            "reporter_id": "user-2",
            "priority": Task.Priority.P2,
            "status": Task.Status.TODO,
            "task_type": "design",
            "tags": ["urgent", "review"],
            "due_date": date.today() + timedelta(days=7),
            "estimated_hours": Decimal("4.00"),
            "actual_hours": Decimal("2.00"),
        }
        defaults.update(kwargs)
        return Task.objects.create(**defaults)

    return _create


@pytest.fixture
def create_comment(db):
    def _create(task, **kwargs):
        defaults = {
            "task": task,
            "author_id": "user-1",
            "content": "Test comment content",
            "mentions": ["user-2", "user-3"],
        }
        defaults.update(kwargs)
        return TaskComment.objects.create(**defaults)

    return _create


@pytest.fixture
def create_message(tenant_id, db):
    def _create(**kwargs):
        defaults = {
            "tenant_id": tenant_id,
            "sender_id": "user-1",
            "recipient_id": "user-2",
            "content": "Hello there",
        }
        defaults.update(kwargs)
        return Message.objects.create(**defaults)

    return _create


# ── Task Core Service Tests ───────────────────────────────────────


class TestTaskService:
    def test_create_task(self, tenant_id, db):
        task = task_service.create_task(
            tenant_id=tenant_id,
            title="New Test Task",
            description="A detailed description",
            assignee_id="user-1",
            reporter_id="user-2",
            priority=Task.Priority.P1,
            due_date=date.today() + timedelta(days=3),
            estimated_hours=Decimal("6.00"),
        )
        assert task is not None
        assert task.title == "New Test Task"
        assert Task.objects.filter(id=task.id).exists()

    def test_get_task(self, create_task):
        t = create_task(title="Find Me")
        result = task_service.get_task(t.id, "test-tenant-team")
        assert result is not None
        assert result.title == "Find Me"

    def test_get_task_wrong_tenant(self, create_task):
        t = create_task()
        result = task_service.get_task(t.id, "wrong-tenant")
        assert result is None

    def test_list_tasks(self, create_task):
        create_task(title="Task A")
        create_task(title="Task B")
        result = task_service.list_tasks("test-tenant-team")
        assert result["total"] >= 2

    def test_list_tasks_status_filter(self, create_task):
        create_task(status=Task.Status.TODO, title="Todo Task")
        create_task(status=Task.Status.DONE, title="Done Task")
        result = task_service.list_tasks("test-tenant-team", status=Task.Status.TODO)
        assert all(t.status == Task.Status.TODO for t in result["results"])

    def test_list_tasks_assignee_filter(self, create_task):
        create_task(assignee_id="user-alice", title="Alice Task")
        create_task(assignee_id="user-bob", title="Bob Task")
        result = task_service.list_tasks("test-tenant-team", assignee_id="user-alice")
        assert all(t.assignee_id == "user-alice" for t in result["results"])

    def test_update_task(self, create_task):
        t = create_task(title="Old Title")
        updated = task_service.update_task(
            t.id, {"title": "New Title", "priority": Task.Priority.P0}
        )
        assert updated.title == "New Title"
        assert updated.priority == Task.Priority.P0

    def test_delete_task(self, create_task):
        t = create_task()
        task_service.delete_task(t.id)
        assert not Task.objects.filter(id=t.id).exists()

    def test_create_subtask(self, create_task):
        parent = create_task(title="Parent Task")
        result = task_service.create_subtask(
            task_id=parent.id,
            title="Subtask 1",
        )
        assert result is not None
        parent.refresh_from_db()
        subs = parent.subtasks
        assert len(subs) == 1
        assert subs[0]["title"] == "Subtask 1"

    def test_toggle_subtask(self, create_task):
        parent = create_task(subtasks=[{"id": "1", "title": "Sub A", "done": False}])
        updated = task_service.toggle_subtask(parent.id, "1")
        assert updated is True
        parent.refresh_from_db()
        assert parent.subtasks[0]["done"] is True

    def test_add_task_dependency(self, create_task):
        t1 = create_task(title="First")
        t2 = create_task(title="Second")
        result = task_service.add_task_dependency(t2.id, t1.id)
        assert result is not None
        assert t1.id in result.dependencies


# ── Messaging Service Tests ───────────────────────────────────────


class TestMessagingService:
    def test_send_message(self, tenant_id, db):
        msg = msg_service.send_message(
            tenant_id=tenant_id,
            sender_id="user-1",
            recipient_id="user-2",
            content="Hello World",
        )
        assert msg is not None
        assert msg.content == "Hello World"
        assert Message.objects.filter(id=msg.id).exists()

    def test_get_conversation(self, tenant_id, create_message):
        create_message(sender_id="user-1", recipient_id="user-2")
        create_message(sender_id="user-2", recipient_id="user-1")
        result = msg_service.get_conversation("user-1", "user-2", tenant_id)
        assert result["total"] >= 2

    def test_get_conversation_empty(self, tenant_id):
        result = msg_service.get_conversation("user-a", "user-b", tenant_id)
        assert result["total"] == 0
        assert result["messages"] == []

    def test_mark_message_read(self, create_message):
        m = create_message(is_read=False)
        updated = msg_service.mark_message_read(m.id)
        assert updated.is_read is True
        assert updated.read_at is not None

    def test_list_unread_messages(self, create_message):
        create_message(is_read=False, recipient_id="user-target")
        create_message(is_read=True, recipient_id="user-target")
        result = msg_service.list_unread_messages("user-target", "test-tenant-team")
        assert result["total"] == 1
        assert all(not m.is_read for m in result["messages"])

    def test_delete_message(self, create_message):
        m = create_message()
        msg_service.delete_message(m.id)
        assert not Message.objects.filter(id=m.id).exists()


# ── Workload Service Tests ────────────────────────────────────────


class TestWorkloadService:
    def test_get_user_workload(self, create_task):
        create_task(
            assignee_id="user-wl",
            status=Task.Status.TODO,
            estimated_hours=Decimal("8.00"),
        )
        create_task(
            assignee_id="user-wl",
            status=Task.Status.IN_PROGRESS,
            estimated_hours=Decimal("4.00"),
        )
        result = wl_service.WorkloadService.get_user_workload("test-tenant-team", "user-wl")
        assert result["user_id"] == "user-wl"
        assert result["total_assigned"] == 2
        assert result["total_estimated_hours"] >= Decimal("12.00")

    def test_get_user_workload_empty(self, tenant_id):
        result = wl_service.WorkloadService.get_user_workload(tenant_id, "nonexistent-user")
        assert result["total_assigned"] == 0

    def test_get_team_workload(self, create_task):
        create_task(assignee_id="user-a", status=Task.Status.TODO)
        create_task(assignee_id="user-b", status=Task.Status.TODO)
        result = wl_service.WorkloadService.get_team_workload("test-tenant-team")
        assert result["tenant_id"] == "test-tenant-team"
        assert len(result["user_workloads"]) >= 2

    def test_get_team_workload_specific_users(self, create_task):
        create_task(assignee_id="user-x", title="X Task")
        create_task(assignee_id="user-y", title="Y Task")
        result = wl_service.WorkloadService.get_team_workload(
            "test-tenant-team", user_ids=["user-x", "user-y"]
        )
        assert len(result["user_workloads"]) == 2

    def test_check_capacity_normal(self, create_task):
        create_task(
            assignee_id="user-cap",
            status=Task.Status.TODO,
            estimated_hours=Decimal("10.00"),
            due_date=date.today() + timedelta(days=5),
        )
        result = wl_service.WorkloadService.check_capacity(
            "test-tenant-team",
            user_ids=["user-cap"],
            weekly_capacity=40,
            meeting_hours=8,
            recurring_hours=5,
        )
        assert len(result["user_capacities"]) == 1
        assert result["user_capacities"][0]["status"] == "normal"

    def test_check_capacity_overloaded(self, create_task):
        create_task(
            assignee_id="user-over",
            status=Task.Status.TODO,
            estimated_hours=Decimal("50.00"),
            due_date=date.today() + timedelta(days=5),
        )
        result = wl_service.WorkloadService.check_capacity(
            "test-tenant-team",
            user_ids=["user-over"],
            weekly_capacity=40,
            meeting_hours=8,
            recurring_hours=5,
        )
        assert len(result["overloaded"]) == 1
        assert result["overloaded"][0]["user_id"] == "user-over"

    def test_get_overdue_tasks(self, create_task):
        create_task(
            assignee_id="user-od",
            status=Task.Status.TODO,
            due_date=date.today() - timedelta(days=5),
        )
        result = wl_service.WorkloadService.get_overdue_tasks(
            "test-tenant-team", assignee_id="user-od"
        )
        assert result["total"] >= 1

    def test_get_upcoming_deadlines(self, create_task):
        create_task(
            assignee_id="user-up",
            status=Task.Status.TODO,
            due_date=date.today() + timedelta(days=3),
        )
        result = wl_service.WorkloadService.get_upcoming_deadlines("test-tenant-team", days=7)
        assert result["total"] >= 1

    def test_generate_suggestions_with_overloaded(self, create_task):
        create_task(
            assignee_id="user-over2",
            status=Task.Status.TODO,
            estimated_hours=Decimal("45.00"),
            due_date=date.today() + timedelta(days=5),
        )
        create_task(
            assignee_id="user-under",
            status=Task.Status.TODO,
            estimated_hours=Decimal("2.00"),
            due_date=date.today() + timedelta(days=5),
        )
        result = wl_service.WorkloadService.check_capacity(
            "test-tenant-team",
            user_ids=["user-over2", "user-under"],
        )
        assert len(result["suggestions"]) >= 1

    def test_get_overdue_tasks_none(self, tenant_id):
        result = wl_service.WorkloadService.get_overdue_tasks(
            tenant_id, assignee_id="no-overdue-user"
        )
        assert result["total"] == 0
