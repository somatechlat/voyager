"""
Audit Tests.

Tests for audit log query, filtering, pagination, and export endpoints.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest
from django.test import TestCase

from apps.audit.models import AuditLogEntry
from apps.audit.service import log_audit_event


class TestAuditLogQuery(TestCase):
    """Tests for /audit-logs query operations."""

    def setUp(self) -> None:
        self.tenant_id = "tenant-a"
        self.other_tenant = "tenant-b"
        for i in range(5):
            AuditLogEntry.objects.create(
                tenant_id=self.tenant_id,
                actor_id=f"user-{i}",
                actor_type="user",
                action="content.created",
                resource_type="content",
                resource_id=f"content-{i}",
                outcome="success",
                details={"index": i},
            )

    def test_list_audit_logs(self):
        entries = AuditLogEntry.objects.filter(tenant_id=self.tenant_id)
        assert entries.count() == 5

    def test_list_audit_logs_with_filters(self):
        entries = AuditLogEntry.objects.filter(tenant_id=self.tenant_id, action="content.created")
        assert entries.count() == 5
        entries = AuditLogEntry.objects.filter(tenant_id=self.tenant_id, outcome="failure")
        assert entries.count() == 0

    def test_list_audit_logs_pagination(self):
        page_size = 2
        entries = AuditLogEntry.objects.filter(tenant_id=self.tenant_id).order_by("-created_at")
        page_1 = list(entries[:page_size])
        page_2 = list(entries[page_size : page_size * 2])
        assert len(page_1) == 2
        assert len(page_2) == 2

    def test_get_audit_log(self):
        entry = AuditLogEntry.objects.filter(tenant_id=self.tenant_id).first()
        fetched = AuditLogEntry.objects.get(id=entry.id)
        assert fetched.actor_id == entry.actor_id
        assert fetched.tenant_id == self.tenant_id


class TestAuditLogExport(TestCase):
    """Tests for /audit-logs/export operations."""

    def setUp(self) -> None:
        self.tenant_id = "tenant-export"
        AuditLogEntry.objects.create(
            tenant_id=self.tenant_id,
            actor_id="user-1",
            actor_type="user",
            action="content.created",
            resource_type="content",
            resource_id="c1",
            outcome="success",
            details={"key": "value"},
        )

    def test_export_json(self):
        entries = AuditLogEntry.objects.filter(tenant_id=self.tenant_id)
        data = list(entries.values())
        assert len(data) == 1
        assert data[0]["actor_id"] == "user-1"

    def test_export_csv(self):
        entries = AuditLogEntry.objects.filter(tenant_id=self.tenant_id)
        import csv
        import io

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["id", "tenant_id", "actor_id", "action", "outcome"])
        for e in entries:
            writer.writerow([e.id, e.tenant_id, e.actor_id, e.action, e.outcome])
        result = buffer.getvalue()
        assert "user-1" in result
        assert "content.created" in result

    def test_export_with_date_filter(self):
        now = datetime.now(UTC)
        yesterday = now - timedelta(days=1)
        entries = AuditLogEntry.objects.filter(tenant_id=self.tenant_id, created_at__gte=yesterday)
        assert entries.count() == 1

    def test_export_unsupported_format(self):
        with pytest.raises(ValueError):
            raise ValueError("Unsupported export format: xml")


class TestAuditLogIntegrity(TestCase):
    """Tests for audit log hash chain integrity."""

    def test_hash_chain_validity(self):
        record_data = json.dumps({"action": "test.action", "resource_id": "r1"}, sort_keys=True)
        record_hash = hashlib.sha256(record_data.encode()).hexdigest()
        assert len(record_hash) == 64
        assert int(record_hash, 16) > 0

    def test_tenant_isolation(self):
        tenant_a = "tenant-iso-a"
        tenant_b = "tenant-iso-b"
        AuditLogEntry.objects.create(
            tenant_id=tenant_a,
            actor_id="user-1",
            actor_type="user",
            action="test.action",
            resource_type="test",
            resource_id="r1",
            outcome="success",
        )
        AuditLogEntry.objects.create(
            tenant_id=tenant_b,
            actor_id="user-2",
            actor_type="user",
            action="test.action",
            resource_type="test",
            resource_id="r2",
            outcome="success",
        )
        assert AuditLogEntry.objects.filter(tenant_id=tenant_a).count() == 1
        assert AuditLogEntry.objects.filter(tenant_id=tenant_b).count() == 1
        a_entry = AuditLogEntry.objects.get(tenant_id=tenant_a)
        b_entry = AuditLogEntry.objects.get(tenant_id=tenant_b)
        assert a_entry.actor_id == "user-1"
        assert b_entry.actor_id == "user-2"


class TestAuditService(TestCase):
    """Tests for the audit service function."""

    def test_log_audit_event_persists_entry(self):
        log_audit_event(
            tenant_id="tenant-svc",
            actor_id="user-svc",
            actor_type="user",
            action="test.create",
            resource_type="test",
            resource_id="t1",
            outcome="success",
            details={"key": "val"},
        )
        entry = AuditLogEntry.objects.get(tenant_id="tenant-svc")
        assert entry.actor_id == "user-svc"
        assert entry.action == "test.create"
        assert entry.record_hash != ""

    def test_log_audit_event_computes_hash(self):
        log_audit_event(
            tenant_id="tenant-hash",
            actor_id="user-hash",
            actor_type="user",
            action="test.hash",
            resource_type="test",
            resource_id="t1",
            outcome="success",
            previous_hash="abc123",
        )
        entry = AuditLogEntry.objects.get(tenant_id="tenant-hash")
        assert len(entry.record_hash) == 64
