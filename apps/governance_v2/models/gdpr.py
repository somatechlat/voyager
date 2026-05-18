"""GDPR consent and DSR request models."""

from __future__ import annotations

from django.db import models


class GDPRConsent(models.Model):
    """Consent record for GDPR compliance.

    Tracks user consent for analytics, marketing, personalization,
    and third-party data sharing with full audit trail.

    Attributes:
        id: Auto-incrementing primary key.
        user_id: UUID string of the consenting user.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        consent_type: Category of consent (analytics, marketing, etc.).
        granted: Whether consent was given or withdrawn.
        source: Origin of the consent record (e.g. 'user_settings').
        ip_address: IP address of the user when consent was recorded.
        user_agent: Browser user agent string.
        created_at: Timestamp when the record was created.
    """

    class ConsentType(models.TextChoices):
        """Supported consent categories."""

        ANALYTICS = "analytics", "Analytics"
        MARKETING = "marketing", "Marketing"
        PERSONALIZATION = "personalization", "Personalization"
        THIRD_PARTY = "third_party", "Third-Party Sharing"
        ESSENTIAL = "essential", "Essential"

    id = models.BigAutoField(primary_key=True, editable=False)
    user_id = models.CharField(
        max_length=256, db_index=True, help_text="UUID string of the consenting user"
    )
    tenant_id = models.CharField(
        max_length=128, db_index=True, help_text="Tenant identifier for multi-tenancy isolation"
    )
    consent_type = models.CharField(
        max_length=50, choices=ConsentType.choices, help_text="Category of consent"
    )
    granted = models.BooleanField(help_text="Whether consent was given or withdrawn")
    source = models.CharField(blank=True, max_length=50, help_text="Origin of the consent record")
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, help_text="IP address of the user when consent was recorded"
    )
    user_agent = models.TextField(blank=True, help_text="Browser user agent string")
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="Timestamp when the record was created"
    )

    class Meta:
        db_table = "voyager_gdpr_consent"
        verbose_name = "GDPR Consent"
        verbose_name_plural = "GDPR Consents"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id", "consent_type", "-created_at"]),
            models.Index(fields=["tenant_id", "consent_type", "-created_at"]),
        ]

    def __str__(self) -> str:
        status = "granted" if self.granted else "withdrawn"
        return f"{self.user_id} - {self.consent_type} ({status})"


class DSRRequest(models.Model):
    """Data Subject Request under GDPR / CCPA.

    Tracks access, erasure, and portability requests with SLA deadlines.

    Attributes:
        id: Auto-incrementing primary key.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        user_id: UUID string of the data subject.
        email: Email address of the data subject.
        request_type: Type of DSR (access, erasure, portability).
        status: Current processing status.
        deadline: SLA deadline for processing.
        completed_at: Timestamp when the request was fulfilled.
        verified_at: Timestamp when the requester's identity was verified.
        processed_by: User ID of the processor.
        notes: Internal processing notes.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    class RequestType(models.TextChoices):
        """Supported data subject request types."""

        ACCESS = "access", "Access"
        ERASURE = "erasure", "Erasure (Right to be Forgotten)"
        PORTABILITY = "portability", "Data Portability"

    class Status(models.TextChoices):
        """Processing status for a DSR."""

        RECEIVED = "received", "Received"
        PENDING_VERIFICATION = "pending_verification", "Pending Identity Verification"
        IN_PROGRESS = "in_progress", "In Progress"
        ON_HOLD = "on_hold", "On Hold"
        COMPLETED = "completed", "Completed"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128, db_index=True, help_text="Tenant identifier for multi-tenancy isolation"
    )
    user_id = models.CharField(
        max_length=256, blank=True, db_index=True, help_text="UUID string of the data subject"
    )
    email = models.EmailField(max_length=255, help_text="Email address of the data subject")
    request_type = models.CharField(
        max_length=20, choices=RequestType.choices, help_text="Type of data subject request"
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.RECEIVED,
        help_text="Current processing status",
    )
    deadline = models.DateTimeField(help_text="SLA deadline for processing the request")
    completed_at = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp when the request was fulfilled"
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the requester's identity was verified",
    )
    processed_by = models.CharField(
        max_length=256,
        blank=True,
        help_text="User ID of the processor who handled the request",
    )
    notes = models.TextField(blank=True, help_text="Internal processing notes")
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="Timestamp when the record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, db_index=True, help_text="Timestamp when the record was last updated"
    )

    class Meta:
        db_table = "voyager_dsr_request"
        verbose_name = "DSR Request"
        verbose_name_plural = "DSR Requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status", "deadline"]),
            models.Index(fields=["tenant_id", "request_type", "status"]),
            models.Index(fields=["user_id", "-created_at"]),
            models.Index(fields=["email", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.request_type} - {self.email} ({self.status})"
