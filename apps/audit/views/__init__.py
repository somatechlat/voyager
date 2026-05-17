"""Audit Log API views for Voyager.

Creates the Ninja router and registers all endpoint functions from
submodules for logs, export, and integrity verification.
"""

from ninja import Router

from apps.audit.serializers import (
    AuditLogListResponse,
    AuditLogSchema,
    AuditLogStatsSchema,
    BulkAuditLogResponse,
    HashChainStatusSchema,
)
from apps.rbac.auth import VoyagerKeycloakBearer

from .export import export_audit_logs
from .integrity import get_audit_stats, verify_chain
from .logs import (
    create_audit_entry,
    create_bulk_audit_entries,
    get_audit_log_entry,
    query_audit_logs,
)

router = Router(auth=VoyagerKeycloakBearer())

# Log query and creation endpoints
router.get("/audit-logs", response=AuditLogListResponse)(query_audit_logs)
router.get("/audit-logs/{entry_id}", response=AuditLogSchema)(get_audit_log_entry)
router.post("/audit-logs")(create_audit_entry)
router.post("/audit-logs/bulk", response=BulkAuditLogResponse)(create_bulk_audit_entries)

# Export endpoints
router.get("/audit-logs/export")(export_audit_logs)

# Statistics and integrity endpoints
router.get("/audit-logs/stats", response=AuditLogStatsSchema)(get_audit_stats)
router.post("/audit-logs/verify", response=HashChainStatusSchema)(verify_chain)
