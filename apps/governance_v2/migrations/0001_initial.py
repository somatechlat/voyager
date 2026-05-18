"""Initial migration for the Governance v2 module.

Creates BrandSafetyRule, ComplianceRule, GDPRConsent, DSRRequest,
ApprovalGate, ApprovalRequest, DataResidencyConfig, and
CrossBorderTransfer models.
"""

from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Initial migration creating all governance models."""

    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="BrandSafetyRule",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        max_length=128,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=255,
                        help_text="Human-readable rule name",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Optional explanation of the rule's purpose",
                    ),
                ),
                (
                    "rule_type",
                    models.CharField(
                        choices=[
                            ("profanity", "Profanity Filter"),
                            ("sensitive_topic", "Sensitive Topic Filter"),
                            ("competitor", "Competitor Mention Filter"),
                            ("medical_claim", "Medical Claim Check"),
                            ("financial_promise", "Financial Promise Check"),
                            ("disclaimer", "Required Disclaimer Check"),
                            ("custom", "Custom Rule"),
                        ],
                        max_length=32,
                        help_text="Category of brand safety check",
                    ),
                ),
                (
                    "conditions",
                    models.JSONField(
                        default=dict,
                        help_text="JSON conditions (patterns, word lists, thresholds)",
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("block", "Block"),
                            ("flag", "Flag for Review"),
                            ("warn", "Warn Only"),
                        ],
                        default="flag",
                        max_length=20,
                        help_text="Response action when the rule triggers",
                    ),
                ),
                (
                    "severity",
                    models.CharField(
                        choices=[
                            ("critical", "Critical"),
                            ("high", "High"),
                            ("medium", "Medium"),
                            ("low", "Low"),
                        ],
                        default="high",
                        max_length=20,
                        help_text="Severity level of violations from this rule",
                    ),
                ),
                (
                    "enabled",
                    models.BooleanField(
                        default=True,
                        help_text="Whether the rule is active",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_brand_safety_rule",
                "verbose_name": "Brand Safety Rule",
                "verbose_name_plural": "Brand Safety Rules",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="brandsafetyrule",
            index=models.Index(
                fields=["tenant_id", "rule_type", "enabled"],
                name="voyager_bsr_tenant_type_en",
            ),
        ),
        migrations.AddIndex(
            model_name="brandsafetyrule",
            index=models.Index(
                fields=["tenant_id", "severity", "enabled"],
                name="voyager_bsr_tenant_sev_en",
            ),
        ),
        migrations.CreateModel(
            name="ComplianceRule",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        max_length=128,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "industry",
                    models.CharField(
                        choices=[
                            ("healthcare", "Healthcare"),
                            ("finance", "Finance"),
                            ("advertising", "Advertising"),
                            ("children", "Children's Content"),
                            ("alcohol", "Alcohol"),
                            ("cannabis", "Cannabis"),
                            ("general", "General"),
                        ],
                        max_length=32,
                        help_text="Target industry sector",
                    ),
                ),
                (
                    "regulation",
                    models.CharField(
                        max_length=100,
                        help_text="Regulation code (e.g. 'FDA 21 CFR 202')",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=255,
                        help_text="Human-readable rule name",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Detailed explanation of the requirement",
                    ),
                ),
                (
                    "check_type",
                    models.CharField(
                        blank=True,
                        max_length=50,
                        help_text="Mechanism used to validate compliance",
                    ),
                ),
                (
                    "check_config",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="JSON configuration for the compliance check",
                    ),
                ),
                (
                    "severity",
                    models.CharField(
                        choices=[
                            ("critical", "Critical"),
                            ("high", "High"),
                            ("medium", "Medium"),
                            ("low", "Low"),
                        ],
                        default="high",
                        max_length=20,
                        help_text="Severity level of violations",
                    ),
                ),
                (
                    "legal_reference",
                    models.TextField(
                        blank=True,
                        help_text="Citation to the legal text",
                    ),
                ),
                (
                    "remediation",
                    models.TextField(
                        blank=True,
                        help_text="Steps to resolve a violation",
                    ),
                ),
                (
                    "enabled",
                    models.BooleanField(
                        default=True,
                        help_text="Whether the rule is active",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_compliance_rule",
                "verbose_name": "Compliance Rule",
                "verbose_name_plural": "Compliance Rules",
                "ordering": ["industry", "regulation", "name"],
            },
        ),
        migrations.AddIndex(
            model_name="compliancerule",
            index=models.Index(
                fields=["tenant_id", "industry", "enabled"],
                name="voyager_cr_tenant_ind_en",
            ),
        ),
        migrations.AddIndex(
            model_name="compliancerule",
            index=models.Index(
                fields=["tenant_id", "regulation", "enabled"],
                name="voyager_cr_tenant_reg_en",
            ),
        ),
        migrations.AddIndex(
            model_name="compliancerule",
            index=models.Index(
                fields=["tenant_id", "severity", "enabled"],
                name="voyager_cr_tenant_sev_en",
            ),
        ),
        migrations.CreateModel(
            name="GDPRConsent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "user_id",
                    models.CharField(
                        db_index=True,
                        max_length=256,
                        help_text="UUID string of the consenting user",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        max_length=128,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "consent_type",
                    models.CharField(
                        choices=[
                            ("analytics", "Analytics"),
                            ("marketing", "Marketing"),
                            ("personalization", "Personalization"),
                            ("third_party", "Third-Party Sharing"),
                            ("essential", "Essential"),
                        ],
                        max_length=50,
                        help_text="Category of consent",
                    ),
                ),
                (
                    "granted",
                    models.BooleanField(
                        help_text="Whether consent was given or withdrawn",
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        blank=True,
                        max_length=50,
                        help_text="Origin of the consent record",
                    ),
                ),
                (
                    "ip_address",
                    models.GenericIPAddressField(
                        blank=True,
                        null=True,
                        help_text="IP address of the user when consent was recorded",
                    ),
                ),
                (
                    "user_agent",
                    models.TextField(
                        blank=True,
                        help_text="Browser user agent string",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_gdpr_consent",
                "verbose_name": "GDPR Consent",
                "verbose_name_plural": "GDPR Consents",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="gdprconsent",
            index=models.Index(
                fields=["user_id", "consent_type", "-created_at"],
                name="voyager_gc_user_type_created",
            ),
        ),
        migrations.AddIndex(
            model_name="gdprconsent",
            index=models.Index(
                fields=["tenant_id", "consent_type", "-created_at"],
                name="voyager_gc_tenant_type_created",
            ),
        ),
        migrations.CreateModel(
            name="DataResidencyConfig",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        max_length=128,
                        unique=True,
                        help_text="Tenant identifier (unique, one config per tenant)",
                    ),
                ),
                (
                    "primary_region",
                    models.CharField(
                        max_length=50,
                        help_text="Primary data storage region code (e.g. 'eu-west-1')",
                    ),
                ),
                (
                    "allowed_regions",
                    models.JSONField(
                        default=list,
                        help_text="JSON list of permitted region codes",
                    ),
                ),
                (
                    "data_types",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="JSON map of data categories to residency rules",
                    ),
                ),
                (
                    "restriction_level",
                    models.CharField(
                        choices=[
                            ("standard", "Standard"),
                            ("restricted", "Restricted"),
                            ("strict", "Strict (No Cross-Border)"),
                        ],
                        default="standard",
                        max_length=20,
                        help_text="Restriction classification for data transfers",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_data_residency_config",
                "verbose_name": "Data Residency Config",
                "verbose_name_plural": "Data Residency Configs",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="dataresidencyconfig",
            index=models.Index(
                fields=["tenant_id", "primary_region"],
                name="voyager_drc_tenant_region",
            ),
        ),
        migrations.CreateModel(
            name="ApprovalGate",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        max_length=128,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=255,
                        help_text="Human-readable gate name",
                    ),
                ),
                (
                    "operations",
                    models.JSONField(
                        default=list,
                        help_text="List of operations this gate applies to",
                    ),
                ),
                (
                    "conditions",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="JSON conditions for when the gate triggers",
                    ),
                ),
                (
                    "approvers",
                    models.JSONField(
                        default=list,
                        help_text="JSON list of approver definitions (roles or users)",
                    ),
                ),
                (
                    "require_all",
                    models.BooleanField(
                        default=True,
                        help_text="Whether all approvers must approve (vs. any one)",
                    ),
                ),
                (
                    "timeout_hours",
                    models.IntegerField(
                        default=48,
                        help_text="Hours before auto-escalation",
                    ),
                ),
                (
                    "escalation",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="JSON escalation configuration",
                    ),
                ),
                (
                    "override_config",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="JSON override policy configuration",
                    ),
                ),
                (
                    "enabled",
                    models.BooleanField(
                        default=True,
                        help_text="Whether the gate is active",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_approval_gate",
                "verbose_name": "Approval Gate",
                "verbose_name_plural": "Approval Gates",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="approvalgate",
            index=models.Index(
                fields=["tenant_id", "enabled"],
                name="voyager_ag_tenant_enabled",
            ),
        ),
        migrations.CreateModel(
            name="DSRRequest",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        max_length=128,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "user_id",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        max_length=256,
                        help_text="UUID string of the data subject",
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        max_length=255,
                        help_text="Email address of the data subject",
                    ),
                ),
                (
                    "request_type",
                    models.CharField(
                        choices=[
                            ("access", "Access"),
                            ("erasure", "Erasure (Right to be Forgotten)"),
                            ("portability", "Data Portability"),
                        ],
                        max_length=20,
                        help_text="Type of data subject request",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("received", "Received"),
                            ("pending_verification", "Pending Identity Verification"),
                            ("in_progress", "In Progress"),
                            ("on_hold", "On Hold"),
                            ("completed", "Completed"),
                            ("rejected", "Rejected"),
                            ("expired", "Expired"),
                        ],
                        default="received",
                        max_length=30,
                        help_text="Current processing status",
                    ),
                ),
                (
                    "deadline",
                    models.DateTimeField(
                        help_text="SLA deadline for processing the request",
                    ),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        help_text="Timestamp when the request was fulfilled",
                    ),
                ),
                (
                    "verified_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        help_text="Timestamp when the requester's identity was verified",
                    ),
                ),
                (
                    "processed_by",
                    models.CharField(
                        blank=True,
                        max_length=256,
                        help_text="User ID of the processor who handled the request",
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        help_text="Internal processing notes",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_dsr_request",
                "verbose_name": "DSR Request",
                "verbose_name_plural": "DSR Requests",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="dsrrequest",
            index=models.Index(
                fields=["tenant_id", "status", "deadline"],
                name="voyager_dsr_tenant_stat_dead",
            ),
        ),
        migrations.AddIndex(
            model_name="dsrrequest",
            index=models.Index(
                fields=["tenant_id", "request_type", "status"],
                name="voyager_dsr_tenant_type_stat",
            ),
        ),
        migrations.AddIndex(
            model_name="dsrrequest",
            index=models.Index(
                fields=["user_id", "-created_at"],
                name="voyager_dsr_user_created",
            ),
        ),
        migrations.AddIndex(
            model_name="dsrrequest",
            index=models.Index(
                fields=["email", "-created_at"],
                name="voyager_dsr_email_created",
            ),
        ),
        migrations.CreateModel(
            name="CrossBorderTransfer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        max_length=128,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "data_type",
                    models.CharField(
                        max_length=50,
                        help_text="Category of data being transferred",
                    ),
                ),
                (
                    "source_region",
                    models.CharField(
                        max_length=50,
                        help_text="Origin region code",
                    ),
                ),
                (
                    "target_region",
                    models.CharField(
                        max_length=50,
                        help_text="Destination region code",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("allowed", "Allowed"),
                            ("blocked", "Blocked"),
                            ("logged", "Logged"),
                        ],
                        max_length=20,
                        help_text="Result of the transfer check",
                    ),
                ),
                (
                    "reason",
                    models.TextField(
                        blank=True,
                        help_text="Human-readable explanation of the decision",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_cross_border_transfer",
                "verbose_name": "Cross-Border Transfer",
                "verbose_name_plural": "Cross-Border Transfers",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="crossbordertransfer",
            index=models.Index(
                fields=["tenant_id", "source_region", "target_region"],
                name="voyager_cbt_tenant_regions",
            ),
        ),
        migrations.AddIndex(
            model_name="crossbordertransfer",
            index=models.Index(
                fields=["tenant_id", "status", "-created_at"],
                name="voyager_cbt_tenant_stat_created",
            ),
        ),
        migrations.CreateModel(
            name="ApprovalRequest",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        max_length=128,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "requester_id",
                    models.CharField(
                        max_length=256,
                        help_text="User ID who initiated the request",
                    ),
                ),
                (
                    "requester_email",
                    models.EmailField(
                        blank=True,
                        max_length=255,
                        help_text="Email of the requester",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("escalated", "Escalated"),
                            ("overridden", "Overridden"),
                        ],
                        default="pending",
                        max_length=20,
                        help_text="Current status of the request",
                    ),
                ),
                (
                    "approved_by",
                    models.JSONField(
                        default=list,
                        help_text="JSON list of user IDs who have approved",
                    ),
                ),
                (
                    "rejected_by",
                    models.CharField(
                        blank=True,
                        max_length=256,
                        help_text="User ID of the rejecter (if rejected)",
                    ),
                ),
                (
                    "justification",
                    models.TextField(
                        blank=True,
                        help_text="Reason text for the request",
                    ),
                ),
                (
                    "rejection_reason",
                    models.TextField(
                        blank=True,
                        help_text="Reason text for rejection",
                    ),
                ),
                (
                    "escalated_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        help_text="Timestamp when escalation occurred",
                    ),
                ),
                (
                    "escalated_to",
                    models.CharField(
                        blank=True,
                        max_length=256,
                        help_text="User/role the request was escalated to",
                    ),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        help_text="Timestamp when the request was finalized",
                    ),
                ),
                (
                    "due_at",
                    models.DateTimeField(
                        help_text="SLA deadline for approval",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "gate",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="requests",
                        to="governance_v2.approvalgate",
                        help_text="The approval gate this request is for",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_approval_request",
                "verbose_name": "Approval Request",
                "verbose_name_plural": "Approval Requests",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="approvalrequest",
            index=models.Index(
                fields=["tenant_id", "status", "due_at"],
                name="voyager_ar_tenant_stat_due",
            ),
        ),
        migrations.AddIndex(
            model_name="approvalrequest",
            index=models.Index(
                fields=["gate", "status"],
                name="voyager_ar_gate_status",
            ),
        ),
        migrations.AddIndex(
            model_name="approvalrequest",
            index=models.Index(
                fields=["requester_id", "-created_at"],
                name="voyager_ar_requester_created",
            ),
        ),
    ]
