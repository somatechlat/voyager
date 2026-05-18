"""Governance v2 API views.

Registers all governance endpoint functions from submodules:
brand safety scanning, compliance rules, GDPR/DSR management,
approval workflows, and data residency.
"""

from ninja import Router

from apps.governance_v2.serializers import (
    ApprovalRequestListResponse,
    ApprovalRequestSchema,
    ComplianceCheckResponse,
    ComplianceRuleListResponse,
    ComplianceRuleSchema,
    ConsentRecordSchema,
    ConsentStatusResponse,
    ContentScanResponse,
    DSRListResponse,
    DSRRequestSchema,
)
from apps.rbac.auth import VoyagerKeycloakBearer

from .approval import (
    approve_request,
    create_approval,
    list_approvals,
)
from .brand_safety import scan_content
from .compliance import (
    check_compliance,
    create_compliance_rule,
    list_compliance_rules,
    update_compliance_rule,
)
from .gdpr import (
    list_dsr_requests,
    list_dsrf,
    record_consent,
    submit_dsr,
    update_dsr,
)

router = Router(auth=VoyagerKeycloakBearer())

# Brand safety endpoints
router.post("/scan", response=ContentScanResponse, tags=["Brand Safety"])(scan_content)

# Compliance rule endpoints
router.get("/rules", response=ComplianceRuleListResponse, tags=["Compliance"])(
    list_compliance_rules
)
router.post("/rules", response=ComplianceRuleSchema, tags=["Compliance"])(create_compliance_rule)
router.put("/rules/{rule_id}", response=ComplianceRuleSchema, tags=["Compliance"])(
    update_compliance_rule
)
router.post("/rules/check", response=ComplianceCheckResponse, tags=["Compliance"])(check_compliance)

# GDPR consent endpoints
router.post("/gdpr/consent", response=ConsentRecordSchema, tags=["GDPR"])(record_consent)
router.get("/gdpr/consent/{user_id}/{tenant_id}", response=ConsentStatusResponse, tags=["GDPR"])(
    list_dsrf
)

# DSR endpoints
router.get("/gdpr/dsr", response=DSRListResponse, tags=["GDPR"])(list_dsr_requests)
router.post("/gdpr/dsr", response=DSRRequestSchema, tags=["GDPR"])(submit_dsr)
router.put("/gdpr/dsr/{dsr_id}", response=DSRRequestSchema, tags=["GDPR"])(update_dsr)

# Approval endpoints
router.get("/approvals", response=ApprovalRequestListResponse, tags=["Approvals"])(list_approvals)
router.post("/approvals", response=ApprovalRequestSchema, tags=["Approvals"])(create_approval)
router.post("/approvals/{request_id}/action", response=ApprovalRequestSchema, tags=["Approvals"])(
    approve_request
)
