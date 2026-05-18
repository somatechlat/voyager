"""Pydantic schemas (Django Ninja Serializers) for Governance v2.

Defines request/response models for brand safety scanning, compliance rules,
GDPR consent and DSR management, approval workflows, and data residency.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ninja import Schema

# ---------------------------------------------------------------------------
# Brand Safety schemas
# ---------------------------------------------------------------------------


class BrandSafetyViolation(Schema):
    """A single brand safety violation found during content scanning."""

    type: str
    severity: str
    message: str
    details: dict[str, Any] = {}


class ContentScanRequest(Schema):
    """Request body for scanning content against brand safety rules."""

    content: str
    tenant_id: str
    industry: str = "general"
    content_type: str = "text"
    metadata: dict[str, Any] = {}


class ContentScanResponse(Schema):
    """Response containing content scan results."""

    passed: bool
    action: str
    violations: list[BrandSafetyViolation]
    scan_timestamp: datetime


class BrandSafetyRuleSchema(Schema):
    """Schema for a brand safety rule."""

    id: int
    tenant_id: str
    name: str
    description: str
    rule_type: str
    conditions: dict[str, Any]
    action: str
    severity: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class BrandSafetyRuleCreateSchema(Schema):
    """Request body for creating a brand safety rule."""

    name: str
    description: str = ""
    rule_type: str
    conditions: dict[str, Any] = {}
    action: str = "flag"
    severity: str = "high"
    enabled: bool = True


class BrandSafetyRuleUpdateSchema(Schema):
    """Request body for updating a brand safety rule."""

    name: str | None = None
    description: str | None = None
    conditions: dict[str, Any] | None = None
    action: str | None = None
    severity: str | None = None
    enabled: bool | None = None


# ---------------------------------------------------------------------------
# Compliance schemas
# ---------------------------------------------------------------------------


class ComplianceRuleSchema(Schema):
    """Schema for an industry compliance rule."""

    id: int
    tenant_id: str
    industry: str
    regulation: str
    name: str
    description: str
    check_type: str
    check_config: dict[str, Any]
    severity: str
    legal_reference: str
    remediation: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class ComplianceRuleCreateSchema(Schema):
    """Request body for creating a compliance rule."""

    industry: str
    regulation: str
    name: str
    description: str = ""
    check_type: str = ""
    check_config: dict[str, Any] = {}
    severity: str = "high"
    legal_reference: str = ""
    remediation: str = ""
    enabled: bool = True


class ComplianceRuleUpdateSchema(Schema):
    """Request body for updating a compliance rule."""

    industry: str | None = None
    regulation: str | None = None
    name: str | None = None
    description: str | None = None
    check_type: str | None = None
    check_config: dict[str, Any] | None = None
    severity: str | None = None
    legal_reference: str | None = None
    remediation: str | None = None
    enabled: bool | None = None


class ComplianceCheckResult(Schema):
    """Result of a compliance check against a rule."""

    rule_id: int
    rule_name: str
    regulation: str
    passed: bool
    severity: str
    description: str
    violation: str = ""
    remediation: str = ""


class ComplianceCheckRequest(Schema):
    """Request body for running a compliance check."""

    content: str
    tenant_id: str
    industry: str
    regulations: list[str] = []


class ComplianceCheckResponse(Schema):
    """Response containing compliance check results."""

    content_id: str = ""
    industry: str
    regulations: list[str]
    overall_compliant: bool
    violations: list[ComplianceCheckResult]
    checked_at: datetime


class ComplianceRuleListResponse(Schema):
    """Paginated response for compliance rule listing."""

    items: list[ComplianceRuleSchema]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# GDPR / Consent schemas
# ---------------------------------------------------------------------------


class ConsentRecordSchema(Schema):
    """Schema for a GDPR consent record."""

    id: int
    user_id: str
    tenant_id: str
    consent_type: str
    granted: bool
    source: str
    ip_address: str | None
    user_agent: str
    created_at: datetime


class ConsentRecordRequest(Schema):
    """Request body for recording consent."""

    user_id: str
    tenant_id: str
    consent_type: str
    granted: bool
    source: str = "user_settings"
    ip_address: str | None = None
    user_agent: str = ""


class ConsentStatusResponse(Schema):
    """Response with current consent status for a user."""

    user_id: str
    tenant_id: str
    consents: list[ConsentRecordSchema]


# ---------------------------------------------------------------------------
# DSR schemas
# ---------------------------------------------------------------------------


class DSRRequestSchema(Schema):
    """Schema for a data subject request."""

    id: int
    tenant_id: str
    user_id: str
    email: str
    request_type: str
    status: str
    deadline: datetime
    completed_at: datetime | None
    verified_at: datetime | None
    processed_by: str
    notes: str
    created_at: datetime
    updated_at: datetime


class DSRSubmitRequest(Schema):
    """Request body for submitting a DSR."""

    tenant_id: str
    user_id: str = ""
    email: str
    request_type: str
    notes: str = ""


class DSRUpdateRequest(Schema):
    """Request body for updating a DSR status."""

    status: str | None = None
    notes: str | None = None
    processed_by: str | None = None


class DSRListResponse(Schema):
    """Paginated response for DSR listing."""

    items: list[DSRRequestSchema]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Approval schemas
# ---------------------------------------------------------------------------


class ApprovalGateSchema(Schema):
    """Schema for an approval gate configuration."""

    id: int
    tenant_id: str
    name: str
    operations: list[str]
    conditions: dict[str, Any]
    approvers: list[dict[str, Any]]
    require_all: bool
    timeout_hours: int
    escalation: dict[str, Any]
    override_config: dict[str, Any]
    enabled: bool
    created_at: datetime
    updated_at: datetime


class ApprovalGateCreateSchema(Schema):
    """Request body for creating an approval gate."""

    name: str
    operations: list[str] = []
    conditions: dict[str, Any] = {}
    approvers: list[dict[str, Any]] = []
    require_all: bool = True
    timeout_hours: int = 48
    escalation: dict[str, Any] = {}
    override_config: dict[str, Any] = {}
    enabled: bool = True


class ApprovalRequestSchema(Schema):
    """Schema for an individual approval request."""

    id: int
    gate_id: int
    tenant_id: str
    requester_id: str
    requester_email: str
    status: str
    approved_by: list[str]
    rejected_by: str
    justification: str
    rejection_reason: str
    escalated_at: datetime | None
    escalated_to: str
    completed_at: datetime | None
    due_at: datetime
    created_at: datetime
    updated_at: datetime


class ApprovalRequestCreateSchema(Schema):
    """Request body for creating an approval request."""

    gate_id: int
    tenant_id: str
    requester_id: str
    requester_email: str = ""
    justification: str = ""


class ApprovalActionSchema(Schema):
    """Request body for approving or rejecting a request."""

    action: str
    approver_id: str
    reason: str = ""


class ApprovalRequestListResponse(Schema):
    """Paginated response for approval request listing."""

    items: list[ApprovalRequestSchema]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Data Residency schemas
# ---------------------------------------------------------------------------


class DataResidencyConfigSchema(Schema):
    """Schema for data residency configuration."""

    id: int
    tenant_id: str
    primary_region: str
    allowed_regions: list[str]
    data_types: dict[str, Any]
    restriction_level: str
    created_at: datetime
    updated_at: datetime


class DataResidencyConfigCreateSchema(Schema):
    """Request body for creating a data residency config."""

    tenant_id: str
    primary_region: str
    allowed_regions: list[str]
    data_types: dict[str, Any] = {}
    restriction_level: str = "standard"


class DataResidencyConfigUpdateSchema(Schema):
    """Request body for updating a data residency config."""

    primary_region: str | None = None
    allowed_regions: list[str] | None = None
    data_types: dict[str, Any] | None = None
    restriction_level: str | None = None


class CrossBorderTransferSchema(Schema):
    """Schema for a cross-border transfer log entry."""

    id: int
    tenant_id: str
    data_type: str
    source_region: str
    target_region: str
    status: str
    reason: str
    created_at: datetime


class TransferCheckRequest(Schema):
    """Request body for checking a cross-border transfer."""

    tenant_id: str
    data_type: str
    target_region: str


class TransferCheckResponse(Schema):
    """Response for a cross-border transfer check."""

    allowed: bool
    source_region: str
    target_region: str
    reason: str
