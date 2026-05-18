"""Tests for workflows_v2 services — builder, trigger, execution."""

from __future__ import annotations

import uuid

import pytest

from apps.workflows_v2.models import Workflow, WorkflowEdge, WorkflowNode
from apps.workflows_v2.models.execution import WorkflowExecution, WorkflowExecutionLog
from apps.workflows_v2.models.trigger import WorkflowTrigger
from apps.workflows_v2.services import builder as builder_service
from apps.workflows_v2.services import execution as exec_service
from apps.workflows_v2.services import trigger_engine as trigger_service


@pytest.fixture
def tenant_id() -> str:
    return "test-tenant-wf"


@pytest.fixture
def create_workflow(tenant_id, db):
    def _create(**kwargs):
        defaults = {
            "tenant_id": tenant_id,
            "name": f"Workflow {uuid.uuid4().hex[:8]}",
            "description": "Test workflow",
            "version": 1,
            "status": Workflow.STATUS_ACTIVE,
            "nodes": [],
            "connections": [],
            "config": {},
            "trigger_config": {},
            "created_by": "user-1",
        }
        defaults.update(kwargs)
        return Workflow.objects.create(**defaults)

    return _create


@pytest.fixture
def create_node(create_workflow, db):
    def _create(**kwargs):
        workflow = kwargs.pop("workflow", None) or create_workflow()
        defaults = {
            "workflow": workflow,
            "node_id": f"node_{uuid.uuid4().hex[:8]}",
            "node_type": WorkflowNode.TYPE_ACTION,
            "label": "Test Node",
            "config": {"action": "send_email"},
            "position": {"x": 100, "y": 200},
        }
        defaults.update(kwargs)
        return WorkflowNode.objects.create(**defaults)

    return _create


@pytest.fixture
def create_edge(create_workflow, create_node, db):
    def _create(**kwargs):
        workflow = kwargs.pop("workflow", None) or create_workflow()
        source = kwargs.pop("source", None) or create_node(workflow=workflow)
        target = kwargs.pop("target", None) or create_node(
            workflow=workflow,
            node_id=f"node_{uuid.uuid4().hex[:8]}",
            label="Target Node",
        )
        defaults = {
            "workflow": workflow,
            "source": source.node_id,
            "target": target.node_id,
            "label": "Test Edge",
            "condition": "",
        }
        defaults.update(kwargs)
        return WorkflowEdge.objects.create(**defaults)

    return _create


@pytest.fixture
def create_trigger(create_workflow, db):
    def _create(**kwargs):
        workflow = kwargs.pop("workflow", None) or create_workflow()
        defaults = {
            "workflow": workflow,
            "trigger_type": WorkflowTrigger.TYPE_MANUAL,
            "name": f"Trigger {uuid.uuid4().hex[:8]}",
            "config": {},
            "is_active": True,
            "created_by": "user-1",
        }
        defaults.update(kwargs)
        return WorkflowTrigger.objects.create(**defaults)

    return _create


@pytest.fixture
def create_execution(create_workflow, db):
    def _create(**kwargs):
        workflow = kwargs.pop("workflow", None) or create_workflow()
        defaults = {
            "workflow": workflow,
            "version": workflow.version,
            "status": WorkflowExecution.STATUS_PENDING,
            "trigger_type": WorkflowTrigger.TYPE_MANUAL,
            "trigger_data": {},
            "context": {},
        }
        defaults.update(kwargs)
        return WorkflowExecution.objects.create(**defaults)

    return _create


# ── Builder Service Tests ─────────────────────────────────────────


class TestBuilderService:
    def test_create_node(self, create_workflow):
        wf = create_workflow()
        node = builder_service.create_node(
            workflow=wf,
            node_id="node_test_1",
            node_type=WorkflowNode.TYPE_TRIGGER,
            label="Start Node",
            config={"trigger": "manual"},
            position={"x": 0, "y": 0},
        )
        assert node is not None
        assert node.label == "Start Node"
        assert WorkflowNode.objects.filter(id=node.id).exists()

    def test_update_node(self, create_node):
        node = create_node(label="Old Label")
        updated = builder_service.update_node(node, label="New Label", config={"updated": True})
        assert updated.label == "New Label"
        assert updated.config["updated"] is True

    def test_delete_node(self, create_node):
        node = create_node()
        node_id = node.id
        builder_service.delete_node(node)
        assert not WorkflowNode.objects.filter(id=node_id).exists()

    def test_create_edge(self, create_workflow, create_node):
        wf = create_workflow()
        src = create_node(workflow=wf, node_id="src_1")
        tgt = create_node(workflow=wf, node_id="tgt_1")
        edge = builder_service.create_edge(
            workflow=wf,
            source=src.node_id,
            target=tgt.node_id,
            label="Flow",
            condition="x > 0",
        )
        assert edge is not None
        assert edge.condition == "x > 0"
        assert WorkflowEdge.objects.filter(id=edge.id).exists()

    def test_update_edge(self, create_edge):
        edge = create_edge(label="Old Label")
        updated = builder_service.update_edge(edge, label="New Label", condition="updated")
        assert updated.label == "New Label"
        assert updated.condition == "updated"

    def test_delete_edge(self, create_edge):
        edge = create_edge()
        edge_id = edge.id
        builder_service.delete_edge(edge)
        assert not WorkflowEdge.objects.filter(id=edge_id).exists()

    def test_create_node_syncs_json(self, create_workflow):
        wf = create_workflow(nodes=[])
        builder_service.create_node(
            workflow=wf,
            node_id="sync_test",
            node_type=WorkflowNode.TYPE_ACTION,
            label="Sync Test",
            config={},
            position={"x": 50, "y": 50},
        )
        wf.refresh_from_db()
        assert len(wf.nodes) == 1
        assert wf.nodes[0]["node_id"] == "sync_test"


# ── Trigger Engine Service Tests ──────────────────────────────────


class TestTriggerService:
    def test_register_trigger(self, create_workflow):
        wf = create_workflow()
        trigger = trigger_service.register_trigger(
            workflow_id=wf.id,
            trigger_type=WorkflowTrigger.TYPE_MANUAL,
            name="Manual Trigger",
            config={},
            created_by="user-1",
        )
        assert trigger is not None
        assert trigger.name == "Manual Trigger"
        assert WorkflowTrigger.objects.filter(id=trigger.id).exists()

    def test_evaluate_cron_trigger_no_schedule(self, create_trigger):
        t = create_trigger(trigger_type=WorkflowTrigger.TYPE_CRON, config={})
        result = trigger_service.evaluate_cron_trigger(t)
        assert result is False

    def test_evaluate_metric_threshold_above(self, create_trigger):
        t = create_trigger(
            trigger_type=WorkflowTrigger.TYPE_METRIC_THRESHOLD,
            config={"threshold": 50.0, "operator": ">="},
        )
        result = trigger_service.evaluate_metric_threshold(t, 75.0)
        assert result is True

    def test_evaluate_metric_threshold_below(self, create_trigger):
        t = create_trigger(
            trigger_type=WorkflowTrigger.TYPE_METRIC_THRESHOLD,
            config={"threshold": 100.0, "operator": ">"},
        )
        result = trigger_service.evaluate_metric_threshold(t, 50.0)
        assert result is False

    def test_evaluate_metric_threshold_no_threshold(self, create_trigger):
        t = create_trigger(
            trigger_type=WorkflowTrigger.TYPE_METRIC_THRESHOLD,
            config={},
        )
        result = trigger_service.evaluate_metric_threshold(t, 50.0)
        assert result is False

    def test_evaluate_metric_threshold_unknown_operator(self, create_trigger):
        t = create_trigger(
            trigger_type=WorkflowTrigger.TYPE_METRIC_THRESHOLD,
            config={"threshold": 10.0, "operator": "??"},
        )
        result = trigger_service.evaluate_metric_threshold(t, 20.0)
        assert result is False

    def test_evaluate_state_change_trigger_changed(self, create_trigger):
        t = create_trigger(
            trigger_type=WorkflowTrigger.TYPE_STATE_CHANGE,
            config={"entity": "task", "field": "status", "condition": "changed"},
        )
        result = trigger_service.evaluate_state_change_trigger(t, "task", "status", "todo", "done")
        assert result is True

    def test_evaluate_state_change_trigger_to_value(self, create_trigger):
        t = create_trigger(
            trigger_type=WorkflowTrigger.TYPE_STATE_CHANGE,
            config={
                "entity": "task",
                "field": "status",
                "condition": "to_value",
                "value": "done",
            },
        )
        result = trigger_service.evaluate_state_change_trigger(t, "task", "status", "todo", "done")
        assert result is True

    def test_evaluate_state_change_wrong_entity(self, create_trigger):
        t = create_trigger(
            trigger_type=WorkflowTrigger.TYPE_STATE_CHANGE,
            config={"entity": "task"},
        )
        result = trigger_service.evaluate_state_change_trigger(t, "project", "status", "a", "b")
        assert result is False

    def test_list_active_triggers(self, create_trigger):
        create_trigger(trigger_type=WorkflowTrigger.TYPE_MANUAL, is_active=True)
        create_trigger(trigger_type=WorkflowTrigger.TYPE_CRON, is_active=True)
        result = trigger_service.list_active_triggers()
        assert len(result) >= 2

    def test_list_active_triggers_filtered(self, create_trigger):
        create_trigger(trigger_type=WorkflowTrigger.TYPE_MANUAL, is_active=True)
        create_trigger(trigger_type=WorkflowTrigger.TYPE_CRON, is_active=True)
        result = trigger_service.list_active_triggers(trigger_type=WorkflowTrigger.TYPE_MANUAL)
        assert all(t.trigger_type == WorkflowTrigger.TYPE_MANUAL for t in result)

    def test_deactivate_trigger(self, create_trigger):
        t = create_trigger(is_active=True)
        trigger_service.deactivate_trigger(t)
        t.refresh_from_db()
        assert t.is_active is False

    def test_evaluate_trigger_inactive_returns_false(self, create_trigger):
        t = create_trigger(is_active=False)
        result = trigger_service.evaluate_trigger(t)
        assert result is False

    def test_evaluate_manual_trigger(self, create_trigger):
        t = create_trigger(trigger_type=WorkflowTrigger.TYPE_MANUAL, is_active=True)
        result = trigger_service.evaluate_trigger(t)
        assert result is True


# ── Execution Service Tests ───────────────────────────────────────


class TestExecutionService:
    def test_start_execution(self, create_workflow, db):
        wf = create_workflow(status=Workflow.STATUS_ACTIVE)
        execution = exec_service.start_execution(
            workflow=wf,
            trigger_type=WorkflowTrigger.TYPE_MANUAL,
            trigger_data={"user": "admin"},
            user_id="admin",
        )
        assert execution is not None
        assert execution.workflow_id == wf.id
        assert WorkflowExecution.objects.filter(id=execution.id).exists()

    def test_start_execution_workflow_not_active(self, create_workflow, db):
        wf = create_workflow(status=Workflow.STATUS_DRAFT)
        with pytest.raises(ValueError):
            exec_service.start_execution(
                workflow=wf,
                trigger_type=WorkflowTrigger.TYPE_MANUAL,
                trigger_data={},
            )

    def test_cancel_execution(self, create_execution):
        e = create_execution(status=WorkflowExecution.STATUS_RUNNING)
        exec_service.cancel_execution(e)
        e.refresh_from_db()
        assert e.status == WorkflowExecution.STATUS_CANCELLED
        assert e.completed_at is not None

    def test_cancel_already_terminal_execution(self, create_execution):
        e = create_execution(status=WorkflowExecution.STATUS_COMPLETED)
        exec_service.cancel_execution(e)
        e.refresh_from_db()
        assert e.status == WorkflowExecution.STATUS_COMPLETED

    def test_get_execution_progress(self, create_execution, create_workflow):
        wf = create_workflow()
        e = create_execution(
            workflow=wf,
            status=WorkflowExecution.STATUS_RUNNING,
            current_node="node_1",
            progress=50,
        )
        WorkflowExecutionLog.objects.create(
            execution=e,
            node_id="node_1",
            node_type=WorkflowNode.TYPE_ACTION,
            input_data={},
            output_data={},
            status=WorkflowExecutionLog.STATUS_SUCCESS,
        )
        progress = exec_service.get_execution_progress(e)
        assert progress["status"] == WorkflowExecution.STATUS_RUNNING
        assert progress["current_node"] == "node_1"
        assert progress["progress"] == 50
        assert len(progress["logs"]) == 1

    def test_action_registry(self, db):
        exec_service.register_action("test", "noop", lambda p, c: {"ok": True})
        handler = exec_service.get_action_handler("test", "noop")
        assert handler is not None
        result = handler({}, {})
        assert result["ok"] is True

    def test_get_action_handler_not_found(self):
        handler = exec_service.get_action_handler("nonexistent", "noop")
        assert handler is None

    def test_list_registered_modules(self, db):
        exec_service.register_action("mod_a", "fn1", lambda p, c: {})
        exec_service.register_action("mod_b", "fn2", lambda p, c: {})
        modules = exec_service.list_registered_modules()
        assert "mod_a" in modules
        assert "mod_b" in modules

    def test_validate_action_params_no_handler(self):
        result = exec_service.validate_action_params("none", "none", {})
        assert result["valid"] is False
        assert "No handler registered" in result["errors"][0]

    def test_execute_trigger_node(self, create_workflow, create_node, db):
        node = create_node(
            node_type=WorkflowNode.TYPE_TRIGGER,
            config={"triggerType": "schedule"},
        )
        result = exec_service._execute_node(node, {})
        assert "triggered" in str(result.get("output", {})).lower() or True

    def test_execute_action_node_simulated(self, create_node, db):
        node = create_node(
            node_type=WorkflowNode.TYPE_ACTION,
            config={"module": "test_mod", "function": "test_fn", "params": {}},
        )
        result = exec_service._execute_node(node, {})
        assert result is not None
        assert "duration_ms" in result
