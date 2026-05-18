"""Client and ClientContact models."""

from __future__ import annotations

from django.db import models


class Client(models.Model):
    """A client (company/organisation) managed within Voyager.

    Attributes:
        id: Auto-incrementing primary key.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        name: Client company name.
        slug: URL-safe unique identifier.
        industry: Industry sector the client operates in.
        website: Client website URL.
        logo_url: URL to the client logo image.
        contact_name: Primary contact person's full name.
        contact_email: Primary contact email address.
        contact_phone: Primary contact phone number.
        address: Physical office address.
        billing_address: Billing address (if different from office).
        tax_id: Tax or VAT identification number.
        status: Current client lifecycle status.
        tier: Service tier the client is subscribed to.
        settings: JSON configuration for client-specific settings.
        metadata: Extensible JSON metadata.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    class Status(models.TextChoices):
        """Client lifecycle statuses."""

        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        PAUSED = "paused", "Paused"
        ONBOARDING = "onboarding", "Onboarding"
        CHURNED = "churned", "Churned"

    class Tier(models.TextChoices):
        """Service tiers available to clients."""

        BASIC = "basic", "Basic"
        PRO = "pro", "Pro"
        ENTERPRISE = "enterprise", "Enterprise"

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    name = models.CharField(max_length=255, help_text="Client company name")
    slug = models.SlugField(max_length=255, help_text="URL-safe unique identifier")
    industry = models.CharField(
        max_length=100,
        blank=True,
        help_text="Industry sector (e.g. 'Technology', 'Healthcare')",
    )
    website = models.URLField(blank=True, help_text="Client website URL")
    logo_url = models.URLField(blank=True, help_text="URL to the client logo image")
    contact_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Primary contact person's full name",
    )
    contact_email = models.EmailField(blank=True, help_text="Primary contact email address")
    contact_phone = models.CharField(
        max_length=50,
        blank=True,
        help_text="Primary contact phone number",
    )
    address = models.TextField(blank=True, help_text="Physical office address")
    billing_address = models.TextField(
        blank=True,
        help_text="Billing address (if different from office)",
    )
    tax_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Tax or VAT identification number",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        help_text="Current client lifecycle status",
    )
    tier = models.CharField(
        max_length=20,
        choices=Tier.choices,
        default=Tier.BASIC,
        help_text="Service tier subscription level",
    )
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Client-specific configuration settings",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extensible metadata for custom attributes",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when the record was created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
        help_text="Timestamp when the record was last updated",
    )

    class Meta:
        db_table = "voyager_client"
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "tier"]),
            models.Index(fields=["tenant_id", "slug"]),
            models.Index(fields=["tenant_id", "-created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "slug"],
                name="clients_client_tenant_slug_uniq",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class ClientContact(models.Model):
    """A contact person associated with a client.

    Attributes:
        id: Auto-incrementing primary key.
        client: The parent client this contact belongs to.
        name: Contact person's full name.
        email: Contact email address.
        phone: Contact phone number.
        role: Job role or title at the client company.
        is_primary: Whether this is the primary contact for the client.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="contacts",
        help_text="The parent client this contact belongs to",
    )
    name = models.CharField(max_length=255, help_text="Contact person's full name")
    email = models.EmailField(help_text="Contact email address")
    phone = models.CharField(
        max_length=50,
        blank=True,
        help_text="Contact phone number",
    )
    role = models.CharField(
        max_length=100,
        blank=True,
        help_text="Job role or title (e.g. 'Marketing Director')",
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Whether this is the primary contact for the client",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the record was created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the record was last updated",
    )

    class Meta:
        db_table = "voyager_client_contact"
        verbose_name = "Client Contact"
        verbose_name_plural = "Client Contacts"
        ordering = ["-is_primary", "name"]
        indexes = [
            models.Index(fields=["client", "is_primary"]),
            models.Index(fields=["client", "email"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.client.name})"
