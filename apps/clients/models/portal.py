"""ClientPortal model."""

from __future__ import annotations

from django.db import models

from apps.clients.models.client import Client


class ClientPortal(models.Model):
    """A white-label client portal configuration.

    Attributes:
        id: Auto-incrementing primary key.
        client: The client this portal belongs to.
        slug: URL-safe portal slug.
        branding: JSON branding configuration (colors, logo, fonts).
        custom_domain: Custom domain for the portal.
        is_active: Whether the portal is currently active.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    client = models.OneToOneField(
        Client,
        on_delete=models.CASCADE,
        related_name="portal",
        help_text="The client this portal belongs to",
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        help_text="URL-safe portal slug",
    )
    branding = models.JSONField(
        default=dict,
        blank=True,
        help_text="Branding config: colors, logo, fonts, custom CSS",
    )
    custom_domain = models.CharField(
        max_length=255,
        blank=True,
        help_text="Custom domain (e.g. portal.client.com)",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the portal is currently active",
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
        db_table = "voyager_client_portal"
        verbose_name = "Client Portal"
        verbose_name_plural = "Client Portals"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return f"Portal for {self.client.name}"
