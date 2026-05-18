# Generated initial migration for governance_v2


from django.db import migrations, models


class ConsentType(models.TextChoices):
    ANALYTICS = "analytics", "Analytics"
    MARKETING = "marketing", "Marketing"
    PERSONALIZATION = "personalization", "Personalization"
    THIRD_PARTY = "third_party", "Third-Party Sharing"
    ESSENTIAL = "essential", "Essential"


class RequestType(models.TextChoices):
    ACCESS = "access", "Access"
    ERASURE = "erasure", "Erasure (Right to be Forgotten)"
    PORTABILITY = "portability", "Data Portability"


class Status(models.TextChoices):
    RECEIVED = "received", "Received"
    PENDING_VERIFICATION = "pending_verification", "Pending Identity Verification"
    IN_PROGRESS = "in_progress", "In Progress"
    ON_HOLD = "on_hold", "On Hold"
    COMPLETED = "completed", "Completed"
    REJECTED = "rejected", "Rejected"
    EXPIRED = "expired", "Expired"


class Migration(migrations.Migration):

    initial = True

    dependencies = [("governance_v2", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="GDPRConsent",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "user_id",
                    models.CharField(
                        max_length=256,
                        db_index=True,
                        help_text="UUID string of the consenting user",
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
                    "consent_type",
                    models.CharField(
                        max_length=50,
                        choices=ConsentType.choices,
                        help_text="Category of consent",
                    ),
                ),
                (
                    "granted",
                    models.BooleanField(help_text="Whether consent was given or withdrawn"),
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
                        null=True,
                        blank=True,
                        help_text="IP address of the user when consent was recorded",
                    ),
                ),
                ("user_agent", models.TextField(blank=True, help_text="Browser user agent string")),
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
                "indexes": [
                    models.Index(fields=["user_id", "consent_type", "-created_at"]),
                    models.Index(fields=["tenant_id", "consent_type", "-created_at"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="DSRRequest",
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
                    "user_id",
                    models.CharField(
                        max_length=256,
                        blank=True,
                        db_index=True,
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
                        max_length=20,
                        choices=RequestType.choices,
                        help_text="Type of data subject request",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=30,
                        choices=Status.choices,
                        default=Status.RECEIVED,
                        help_text="Current processing status",
                    ),
                ),
                (
                    "deadline",
                    models.DateTimeField(help_text="SLA deadline for processing the request"),
                ),
                (
                    "completed_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="Timestamp when the request was fulfilled",
                    ),
                ),
                (
                    "verified_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="Timestamp when the requester's identity was verified",
                    ),
                ),
                (
                    "processed_by",
                    models.CharField(
                        max_length=256,
                        blank=True,
                        help_text="User ID of the processor who handled the request",
                    ),
                ),
                ("notes", models.TextField(blank=True, help_text="Internal processing notes")),
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
                "indexes": [
                    models.Index(fields=["tenant_id", "status", "deadline"]),
                    models.Index(fields=["tenant_id", "request_type", "status"]),
                    models.Index(fields=["user_id", "-created_at"]),
                    models.Index(fields=["email", "-created_at"]),
                ],
            },
        ),
    ]
