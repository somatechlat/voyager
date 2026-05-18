"""Initial migration for the Clients CRM module (part 1).

Creates Client, ClientContact, and Project models.
"""

from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Initial migration for clients app — part 1."""

    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="Client",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True, max_length=128,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                ("name", models.CharField(max_length=255, help_text="Client company name")),
                (
                    "slug",
                    models.SlugField(max_length=255, help_text="URL-safe unique identifier"),
                ),
                (
                    "industry",
                    models.CharField(
                        blank=True, max_length=100,
                        help_text="Industry sector (e.g. 'Technology', 'Healthcare')",
                    ),
                ),
                (
                    "website",
                    models.URLField(blank=True, help_text="Client website URL"),
                ),
                (
                    "logo_url",
                    models.URLField(blank=True, help_text="URL to the client logo image"),
                ),
                (
                    "contact_name",
                    models.CharField(
                        blank=True, max_length=255,
                        help_text="Primary contact person's full name",
                    ),
                ),
                (
                    "contact_email",
                    models.EmailField(blank=True, help_text="Primary contact email address"),
                ),
                (
                    "contact_phone",
                    models.CharField(
                        blank=True, max_length=50,
                        help_text="Primary contact phone number",
                    ),
                ),
                (
                    "address",
                    models.TextField(blank=True, help_text="Physical office address"),
                ),
                (
                    "billing_address",
                    models.TextField(
                        blank=True,
                        help_text="Billing address (if different from office)",
                    ),
                ),
                (
                    "tax_id",
                    models.CharField(
                        blank=True, max_length=100,
                        help_text="Tax or VAT identification number",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("inactive", "Inactive"),
                            ("paused", "Paused"),
                            ("onboarding", "Onboarding"),
                            ("churned", "Churned"),
                        ],
                        db_index=True, default="active", max_length=20,
                        help_text="Current client lifecycle status",
                    ),
                ),
                (
                    "tier",
                    models.CharField(
                        choices=[
                            ("basic", "Basic"),
                            ("pro", "Pro"),
                            ("enterprise", "Enterprise"),
                        ],
                        default="basic", max_length=20,
                        help_text="Service tier subscription level",
                    ),
                ),
                (
                    "settings",
                    models.JSONField(
                        blank=True, default=dict,
                        help_text="Client-specific configuration settings",
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        blank=True, default=dict,
                        help_text="Extensible metadata for custom attributes",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_client",
                "verbose_name": "Client",
                "verbose_name_plural": "Clients",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="client",
            index=models.Index(
                fields=["tenant_id", "slug"],
                name="voyager_client_tenant_slug_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="client",
            index=models.Index(
                fields=["tenant_id", "status"],
                name="voyager_client_tenant_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="client",
            index=models.Index(
                fields=["tenant_id", "tier"],
                name="voyager_client_tenant_tier_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="client",
            index=models.Index(
                fields=["tenant_id", "-created_at"],
                name="voyager_client_tenant_created_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="client",
            constraint=models.UniqueConstraint(
                fields=["tenant_id", "slug"],
                name="clients_client_tenant_slug_uniq",
            ),
        ),
        migrations.CreateModel(
            name="ClientContact",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=255, help_text="Contact person's full name")),
                ("email", models.EmailField(help_text="Contact email address")),
                (
                    "phone",
                    models.CharField(
                        blank=True, max_length=50, help_text="Contact phone number",
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        blank=True, max_length=100,
                        help_text="Job role or title (e.g. 'Marketing Director')",
                    ),
                ),
                (
                    "is_primary",
                    models.BooleanField(
                        default=False,
                        help_text="Whether this is the primary contact for the client",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "client",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contacts",
                        to="clients.client",
                        help_text="The parent client this contact belongs to",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_client_contact",
                "verbose_name": "Client Contact",
                "verbose_name_plural": "Client Contacts",
                "ordering": ["-is_primary", "name"],
            },
        ),
        migrations.AddIndex(
            model_name="clientcontact",
            index=models.Index(
                fields=["client", "is_primary"],
                name="voyager_contact_client_primary_idx",
            ),
        ),
        migrations.CreateModel(
            name="Project",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True, max_length=128,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                ("name", models.CharField(max_length=255, help_text="Project name")),
                (
                    "description",
                    models.TextField(blank=True, help_text="Detailed project description"),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("planning", "Planning"),
                            ("active", "Active"),
                            ("completed", "Completed"),
                            ("archived", "Archived"),
                        ],
                        db_index=True, default="planning", max_length=20,
                        help_text="Current project status",
                    ),
                ),
                (
                    "start_date",
                    models.DateField(blank=True, null=True, help_text="Project start date"),
                ),
                (
                    "end_date",
                    models.DateField(
                        blank=True, null=True,
                        help_text="Project end date (estimated or actual)",
                    ),
                ),
                (
                    "budget_amount",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True,
                        help_text="Allocated budget amount",
                    ),
                ),
                (
                    "budget_type",
                    models.CharField(
                        choices=[
                            ("fixed", "Fixed Price"),
                            ("hourly", "Hourly"),
                            ("retainer", "Retainer"),
                            ("hybrid", "Hybrid"),
                        ],
                        default="fixed", max_length=20,
                        help_text="How the project is billed",
                    ),
                ),
                (
                    "manager_id",
                    models.CharField(
                        blank=True, db_index=True, max_length=256,
                        help_text="User ID of the project manager",
                    ),
                ),
                (
                    "team_ids",
                    models.JSONField(
                        blank=True, default=list,
                        help_text="List of team member user IDs",
                    ),
                ),
                (
                    "settings",
                    models.JSONField(
                        blank=True, default=dict,
                        help_text="Project-specific configuration",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "client",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="projects",
                        to="clients.client",
                        help_text="The client this project belongs to",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_project",
                "verbose_name": "Project",
                "verbose_name_plural": "Projects",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="project",
            index=models.Index(
                fields=["tenant_id", "status"],
                name="voyager_project_tenant_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="project",
            index=models.Index(
                fields=["tenant_id", "client", "status"],
                name="voyager_project_tenant_client_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="project",
            index=models.Index(
                fields=["tenant_id", "manager_id"],
                name="voyager_project_tenant_manager_idx",
            ),
        ),
    ]
