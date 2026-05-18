# Generated initial migration for governance_v2


from django.db import migrations, models


class RestrictionLevel(models.TextChoices):
    STANDARD = "standard", "Standard"
    RESTRICTED = "restricted", "Restricted"
    STRICT = "strict", "Strict (No Cross-Border)"


class Status(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    ESCALATED = "escalated", "Escalated"
    OVERRIDDEN = "overridden", "Overridden"


class Migration(migrations.Migration):

    initial = True

    dependencies = [("governance_v2", "0002_additional_models")]

    operations = [
        migrations.CreateModel(
            name="ApprovalGate",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                ("name", models.CharField(max_length=255, help_text="Human-readable gate name")),
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
                        default=dict,
                        blank=True,
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
                        default=dict,
                        blank=True,
                        help_text="JSON escalation configuration",
                    ),
                ),
                (
                    "override_config",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="JSON override policy configuration",
                    ),
                ),
                (
                    "enabled",
                    models.BooleanField(default=True, help_text="Whether the gate is active"),
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
                "indexes": [models.Index(fields=["tenant_id", "enabled"])],
            },
        ),
        migrations.CreateModel(
            name="ApprovalRequest",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "gate",
                    models.ForeignKey(
                        ApprovalGate,
                        on_delete=models.CASCADE,
                        related_name="requests",
                        help_text="The approval gate this request is for",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
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
                        max_length=255,
                        blank=True,
                        help_text="Email of the requester",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.PENDING,
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
                        max_length=256,
                        blank=True,
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
                        null=True,
                        blank=True,
                        help_text="Timestamp when escalation occurred",
                    ),
                ),
                (
                    "escalated_to",
                    models.CharField(
                        max_length=256,
                        blank=True,
                        help_text="User/role the request was escalated to",
                    ),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="Timestamp when the request was finalized",
                    ),
                ),
                ("due_at", models.DateTimeField(help_text="SLA deadline for approval")),
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
                "db_table": "voyager_approval_request",
                "verbose_name": "Approval Request",
                "verbose_name_plural": "Approval Requests",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "status", "due_at"]),
                    models.Index(fields=["gate", "status"]),
                    models.Index(fields=["requester_id", "-created_at"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="DataResidencyConfig",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128,
                        unique=True,
                        db_index=True,
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
                        default=dict,
                        blank=True,
                        help_text="JSON map of data categories to residency rules",
                    ),
                ),
                (
                    "restriction_level",
                    models.CharField(
                        max_length=20,
                        choices=RestrictionLevel.choices,
                        default=RestrictionLevel.STANDARD,
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
                "indexes": [models.Index(fields=["tenant_id", "primary_region"])],
            },
        ),
        migrations.CreateModel(
            name="CrossBorderTransfer",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
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
                ("source_region", models.CharField(max_length=50, help_text="Origin region code")),
                (
                    "target_region",
                    models.CharField(max_length=50, help_text="Destination region code"),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=Status.choices,
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
                "indexes": [
                    models.Index(fields=["tenant_id", "source_region", "target_region"]),
                    models.Index(fields=["tenant_id", "status", "-created_at"]),
                ],
            },
        ),
    ]
