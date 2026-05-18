"""Django Admin for Governance V2 app.

Registers BrandSafetyRule, ComplianceRule, GDPRConsent,
DSRRequest, and ApprovalGate models.
"""

from __future__ import annotations

import json

from django.contrib import admin

from apps.governance_v2.models import (
    ApprovalGate,
    BrandSafetyRule,
    ComplianceCheck,
    ComplianceRule,
    DSRRequest,
    GDPRConsent,
    PolicyVersion,
)


class _JSONMixin:
    """Mixin for formatting JSON fields."""

    @staticmethod
    def _format_json(value: object, max_len: int = 200) -> str:
        if not value:
            return "—"
        if isinstance(value, (dict, list)):
            text = json.dumps(value, indent=2, default=str)
            if len(text) > max_len:
                return text[:max_len] + "..."
            return text
        return str(value)[:max_len]


class _TenantIdMixin:
    """Mixin for shortening tenant_id display."""

    @admin.display(description="Tenant")
    def tenant_id_short(self, obj):
        tid = getattr(obj, "tenant_id", "")
        return tid[:12] + "..." if len(str(tid)) > 12 else str(tid)


class ComplianceCheckInline(admin.TabularInline):
    """Inline for ComplianceCheck within ComplianceRule."""

    model = ComplianceCheck
    extra = 0
    readonly_fields = ("id", "executed_at")


class PolicyVersionInline(admin.TabularInline):
    """Inline for PolicyVersion within ComplianceRule."""

    model = PolicyVersion
    extra = 0
    readonly_fields = ("id", "created_at")


@admin.register(BrandSafetyRule)
class BrandSafetyRuleAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for BrandSafetyRule model."""

    list_display = (
        "name",
        "category",
        "action",
        "is_active",
        "match_count",
        "block_automatically",
        "severity",
        "tenant_id_short",
        "created_at",
    )
    list_filter = (
        "category",
        "action",
        "is_active",
        "block_automatically",
        "severity",
        "created_at",
    )
    search_fields = (
        "name",
        "description",
        "tenant_id",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "match_count",
        "last_match_at",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Keywords")
    def display_keywords(self, obj: BrandSafetyRule) -> str:
        return self._format_json(obj.keywords_json, 200)

    @admin.display(description="Blocked Users")
    def display_blocked(self, obj: BrandSafetyRule) -> str:
        return self._format_json(obj.blocked_users_json, 150)

    @admin.display(description="Match History")
    def display_history(self, obj: BrandSafetyRule) -> str:
        return self._format_json(obj.match_history_json, 200)


@admin.register(ComplianceRule)
class ComplianceRuleAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for ComplianceRule model."""

    list_display = (
        "name",
        "standard",
        "rule_type",
        "applies_to",
        "is_active",
        "check_frequency_days",
        "last_check_status",
        "violation_count",
        "risk_level",
        "tenant_id_short",
    )
    list_filter = (
        "standard",
        "rule_type",
        "applies_to",
        "is_active",
        "risk_level",
        "last_check_status",
        "created_at",
    )
    search_fields = (
        "name",
        "description",
        "check_query",
        "tenant_id",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "violation_count",
        "last_check_at",
        "next_check_due",
        "created_at",
        "updated_at",
    )
    inlines = [ComplianceCheckInline, PolicyVersionInline]

    @admin.display(description="Remediation")
    def display_remediation(self, obj: ComplianceRule) -> str:
        return self._format_json(obj.remediation_steps_json, 200)

    @admin.display(description="Auto Fix")
    def display_auto_fix(self, obj: ComplianceRule) -> str:
        return self._format_json(obj.auto_fix_config, 200)


@admin.register(GDPRConsent)
class GDPRConsentAdmin(_TenantIdMixin, admin.ModelAdmin):
    """Admin for GDPRConsent model."""

    list_display = (
        "user_id_short",
        "consent_type",
        "granted",
        "ip_address",
        "withdrawn",
        "withdrawn_at",
        "tenant_id_short",
        "created_at",
    )
    list_filter = (
        "consent_type",
        "granted",
        "withdrawn",
        "created_at",
    )
    search_fields = (
        "user_id",
        "ip_address",
        "tenant_id",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "granted",
        "withdrawn_at",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "created_at"

    @admin.display(description="User")
    def user_id_short(self, obj: GDPRConsent) -> str:
        return obj.user_id[:12] + "..." if len(obj.user_id) > 12 else obj.user_id


@admin.register(DSRRequest)
class DSRRequestAdmin(_TenantIdMixin, admin.ModelAdmin):
    """Admin for DSRRequest (Data Subject Rights) model."""

    list_display = (
        "user_id_short",
        "request_type",
        "status",
        "priority",
        "data_scope",
        "verified",
        "sla_deadline",
        "completed_at",
        "sla_met",
        "tenant_id_short",
        "created_at",
    )
    list_filter = (
        "request_type",
        "status",
        "priority",
        "data_scope",
        "verified",
        "sla_met",
        "created_at",
    )
    search_fields = (
        "user_id",
        "identity_verification_json",
        "tenant_id",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "completed_at",
        "sla_met",
        "processing_time_ms",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "created_at"

    @admin.display(description="User")
    def user_id_short(self, obj: DSRRequest) -> str:
        return obj.user_id[:12] + "..." if len(obj.user_id) > 12 else obj.user_id


@admin.register(ApprovalGate)
class ApprovalGateAdmin(_JSONMixin, _TenantIdMixin, admin.ModelAdmin):
    """Admin for ApprovalGate model."""

    list_display = (
        "name",
        "entity_type",
        "status",
        "priority",
        "min_approvers",
        "current_approvers",
        "auto_escalate_hours",
        "tenant_id_short",
        "created_at",
    )
    list_filter = (
        "entity_type",
        "status",
        "priority",
        "created_at",
    )
    search_fields = (
        "name",
        "entity_id",
        "tenant_id",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "current_approvers",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Approvers")
    def display_approvers(self, obj: ApprovalGate) -> str:
        return self._format_json(obj.approvers_json, 200)

    @admin.display(description="Votes")
    def display_votes(self, obj: ApprovalGate) -> str:
        return self._format_json(obj.votes_json, 200)

    @admin.display(description="History")
    def display_history(self, obj: ApprovalGate) -> str:
        return self._format_json(obj.history_json, 200)
