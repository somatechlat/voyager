"""Tests for Audit models: AuditLogEntry and AuditLogArchive."""

from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.models import AuditLogArchive, AuditLogEntry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tenant_id() -> str:
    """Return a consistent tenant ID for tests."""
    return "test-tenant-001"


@pytest.fixture
def base_entry(tenant_id: str) -> AuditLogEntry:
    """Create the first audit log entry in a tenant (no previous hash)."""
    entry = AuditLogEntry.objects.create(
        tenant_id=tenant_id,
        actor_id="user-001",
        actor_type=AuditLogEntry.ActorType.USER,
        action="content.created",
        resource_type="content_generation",
        resource_id="res-001",
        outcome=AuditLogEntry.Outcome.SUCCESS,
        details={"before": {}, "after": {"title": "Hello"}},
        previous_hash="",
        entry_hash="",
    )
    # Compute and store hash after creation so timestamp is set
    entry.entry_hash = entry.compute_hash()
    entry.save(update_fields=["entry_hash"])
    return entry


# ---------------------------------------------------------------------------
# AuditLogEntry creation tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_audit_log_entry_creation(base_entry: AuditLogEntry) -> None:
    """AuditLogEntry can be created with all required fields."""
    assert base_entry.id is not None
    assert base_entry.tenant_id == "test-tenant-001"
    assert base_entry.actor_id == "user-001"
    assert base_entry.actor_type == "user"
    assert base_entry.action == "content.created"
    assert base_entry.resource_type == "content_generation"
    assert base_entry.resource_id == "res-001"
    assert base_entry.outcome == "success"


@pytest.mark.django_db
def test_audit_log_entry_str(base_entry: AuditLogEntry) -> None:
    """String representation contains action, actor and resource info."""
    rep = str(base_entry)
    assert "content.created" in rep
    assert "user" in rep
    assert "user-001" in rep
    assert "content_generation" in rep
    assert "res-001" in rep
    assert "success" in rep


@pytest.mark.django_db
def test_audit_log_entry_actor_type_choices(tenant_id: str) -> None:
    """All ActorType choices can be stored."""
    for value, label in AuditLogEntry.ActorType.choices:
        entry = AuditLogEntry.objects.create(
            tenant_id=tenant_id,
            actor_id=f"actor-{value}",
            actor_type=value,
            action="test.action",
            resource_type="test",
            resource_id=f"res-{value}",
            outcome=AuditLogEntry.Outcome.SUCCESS,
            previous_hash="",
            entry_hash="dummy",
        )
        assert entry.actor_type == value


@pytest.mark.django_db
def test_audit_log_entry_outcome_choices(tenant_id: str) -> None:
    """All Outcome choices can be stored."""
    for idx, (value, _label) in enumerate(AuditLogEntry.Outcome.choices):
        entry = AuditLogEntry.objects.create(
            tenant_id=tenant_id,
            actor_id=f"actor-{idx}",
            actor_type=AuditLogEntry.ActorType.USER,
            action="test.action",
            resource_type="test",
            resource_id=f"res-{idx}",
            outcome=value,
            previous_hash="",
            entry_hash=f"hash{idx}",
        )
        assert entry.outcome == value


@pytest.mark.django_db
def test_audit_log_entry_optional_fields(tenant_id: str) -> None:
    """Optional fields (ip_address, user_agent, request_id, session_id) can be blank."""
    entry = AuditLogEntry.objects.create(
        tenant_id=tenant_id,
        actor_id="user-002",
        actor_type=AuditLogEntry.ActorType.SERVICE,
        action="test.action",
        resource_type="test",
        resource_id="res-002",
        outcome=AuditLogEntry.Outcome.FAILURE,
        ip_address=None,
        user_agent="",
        request_id="",
        session_id="",
        previous_hash="",
        entry_hash="x" * 64,
    )
    assert entry.ip_address is None
    assert entry.user_agent == ""


# ---------------------------------------------------------------------------
# Hash chain tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_compute_hash_returns_64_hex_chars(base_entry: AuditLogEntry) -> None:
    """compute_hash returns a 64-character hexadecimal SHA-256 digest."""
    hash_value = base_entry.compute_hash()
    assert len(hash_value) == 64
    assert int(hash_value, 16)  # valid hex


@pytest.mark.django_db
def test_compute_hash_is_deterministic(base_entry: AuditLogEntry) -> None:
    """compute_hash returns the same value for the same data."""
    h1 = base_entry.compute_hash()
    h2 = base_entry.compute_hash()
    assert h1 == h2


@pytest.mark.django_db
def test_compute_hash_changes_with_data(tenant_id: str) -> None:
    """compute_hash produces different values for different data."""
    entry1 = AuditLogEntry.objects.create(
        tenant_id=tenant_id,
        actor_id="user-001",
        actor_type=AuditLogEntry.ActorType.USER,
        action="content.created",
        resource_type="content_generation",
        resource_id="res-001",
        outcome=AuditLogEntry.Outcome.SUCCESS,
        previous_hash="",
        entry_hash="",
    )
    entry2 = AuditLogEntry.objects.create(
        tenant_id=tenant_id,
        actor_id="user-002",
        actor_type=AuditLogEntry.ActorType.USER,
        action="content.created",
        resource_type="content_generation",
        resource_id="res-001",
        outcome=AuditLogEntry.Outcome.SUCCESS,
        previous_hash="",
        entry_hash="",
    )
    assert entry1.compute_hash() != entry2.compute_hash()


@pytest.mark.django_db
def test_verify_hash_true(base_entry: AuditLogEntry) -> None:
    """verify_hash returns True when entry_hash matches computed hash."""
    base_entry.entry_hash = base_entry.compute_hash()
    base_entry.save(update_fields=["entry_hash"])
    assert base_entry.verify_hash() is True


@pytest.mark.django_db
def test_verify_hash_false(base_entry: AuditLogEntry) -> None:
    """verify_hash returns False when entry_hash has been tampered with."""
    base_entry.entry_hash = "0" * 64
    base_entry.save(update_fields=["entry_hash"])
    assert base_entry.verify_hash() is False


@pytest.mark.django_db
def test_verify_chain_first_entry(tenant_id: str) -> None:
    """verify_chain for first entry returns entry_valid=True and chain_valid=None."""
    entry = AuditLogEntry.objects.create(
        tenant_id=tenant_id,
        actor_id="user-001",
        actor_type=AuditLogEntry.ActorType.USER,
        action="content.created",
        resource_type="content_generation",
        resource_id="res-001",
        outcome=AuditLogEntry.Outcome.SUCCESS,
        previous_hash="",
        entry_hash="",
    )
    entry.entry_hash = entry.compute_hash()
    entry.save(update_fields=["entry_hash"])
    result = entry.verify_chain()
    assert result["entry_valid"] is True
    assert result["chain_valid"] is None


@pytest.mark.django_db
def test_verify_chain_linked_entry(base_entry: AuditLogEntry, tenant_id: str) -> None:
    """verify_chain validates correct link between consecutive entries."""
    # Create second entry linking to first
    second = AuditLogEntry.objects.create(
        tenant_id=tenant_id,
        actor_id="user-001",
        actor_type=AuditLogEntry.ActorType.USER,
        action="content.updated",
        resource_type="content_generation",
        resource_id="res-001",
        outcome=AuditLogEntry.Outcome.SUCCESS,
        previous_hash=base_entry.entry_hash,
        entry_hash="",
    )
    second.entry_hash = second.compute_hash()
    second.save(update_fields=["entry_hash"])

    result = second.verify_chain()
    assert result["entry_valid"] is True
    assert result["chain_valid"] is True


@pytest.mark.django_db
def test_verify_chain_broken_link(base_entry: AuditLogEntry, tenant_id: str) -> None:
    """verify_chain detects a broken hash chain (tampered previous_hash)."""
    second = AuditLogEntry.objects.create(
        tenant_id=tenant_id,
        actor_id="user-001",
        actor_type=AuditLogEntry.ActorType.USER,
        action="content.updated",
        resource_type="content_generation",
        resource_id="res-001",
        outcome=AuditLogEntry.Outcome.SUCCESS,
        previous_hash="tampered-hash-value-here",
        entry_hash="",
    )
    second.entry_hash = second.compute_hash()
    second.save(update_fields=["entry_hash"])

    result = second.verify_chain()
    assert result["entry_valid"] is True
    assert result["chain_valid"] is False


# ---------------------------------------------------------------------------
# AuditLogArchive tests
# ---------------------------------------------------------------------------


@pytest.fixture
def archive(tenant_id: str) -> AuditLogArchive:
    """Create and return an AuditLogArchive instance."""
    return AuditLogArchive.objects.create(
        year_month="2024-01",
        tenant_id=tenant_id,
        log_count=1500,
        archive_data=b"compressed-archive-data",
    )


@pytest.mark.django_db
def test_audit_log_archive_creation(archive: AuditLogArchive) -> None:
    """AuditLogArchive can be created with all required fields."""
    assert archive.id is not None
    assert archive.year_month == "2024-01"
    assert archive.tenant_id == "test-tenant-001"
    assert archive.log_count == 1500
    assert archive.archive_data == b"compressed-archive-data"


@pytest.mark.django_db
def test_audit_log_archive_str(archive: AuditLogArchive) -> None:
    """String representation includes tenant, month and log count."""
    assert str(archive) == "test-tenant-001 / 2024-01 (1500 entries)"


@pytest.mark.django_db
def test_audit_log_archive_unique_tenant_month(tenant_id: str) -> None:
    """Duplicate year_month for same tenant raises IntegrityError."""
    AuditLogArchive.objects.create(
        year_month="2024-02",
        tenant_id=tenant_id,
        log_count=100,
        archive_data=b"data",
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            AuditLogArchive.objects.create(
                year_month="2024-02",
                tenant_id=tenant_id,
                log_count=200,
                archive_data=b"data2",
            )


@pytest.mark.django_db
def test_audit_log_archive_different_tenants_same_month() -> None:
    """Same year_month for different tenants is allowed."""
    a1 = AuditLogArchive.objects.create(
        year_month="2024-03",
        tenant_id="tenant-a",
        log_count=100,
        archive_data=b"data",
    )
    a2 = AuditLogArchive.objects.create(
        year_month="2024-03",
        tenant_id="tenant-b",
        log_count=200,
        archive_data=b"data2",
    )
    assert a1.id is not None
    assert a2.id is not None


@pytest.mark.django_db
def test_audit_log_entry_auto_timestamp(tenant_id: str) -> None:
    """AuditLogEntry auto-sets timestamp on creation."""
    before = timezone.now()
    entry = AuditLogEntry.objects.create(
        tenant_id=tenant_id,
        actor_id="user-001",
        actor_type=AuditLogEntry.ActorType.USER,
        action="test.action",
        resource_type="test",
        resource_id="res-001",
        outcome=AuditLogEntry.Outcome.SUCCESS,
        previous_hash="",
        entry_hash="x" * 64,
    )
    after = timezone.now()
    assert before <= entry.timestamp <= after
