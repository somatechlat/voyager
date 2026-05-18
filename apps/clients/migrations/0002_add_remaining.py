"""Second migration for the Clients CRM module.

Creates ProjectMilestone, CommunicationLog, ClientPortal,
and ClientProfitability models with indexes and constraints.
"""

from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Part 2 — remaining models and indexes."""

    dependencies = [("clients", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="ProjectMilestone",
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
                ("name", models.CharField(max_length=255, help_text="Milestone name")),
                (
                    "description",
                    models.TextField(blank=True, help_text="Detailed milestone description"),
                ),
                (
                    "due_date",
                    models.DateField(blank=True, null=True, help_text="When the milestone is due"),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("in_progress", "In Progress"),
                            ("completed", "Completed"),
                            ("missed", "Missed"),
                        ],
                        db_index=True, default="pending", max_length=20,
                        help_text="Current milestone status",
                    ),
                ),
                (
                    "deliverables",
                    models.JSONField(
                        blank=True, default=list,
                        help_text="List of deliverable items with name and status",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, help_text="Timestamp when the record was created",
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
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="milestones",
                        to="clients.project",
                        help_text="The parent project this milestone belongs to",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_project_milestone",
                "verbose_name": "Project Milestone",
                "verbose_name_plural": "Project Milestones",
                "ordering": ["due_date", "name"],
            },
        ),
        migrations.AddIndex(
            model_name="projectmilestone",
            index=models.Index(
                fields=["project", "status"],
                name="voyager_ms_project_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="projectmilestone",
            index=models.Index(
                fields=["project", "due_date"],
                name="voyager_ms_project_due_idx",
            ),
        ),
        migrations.CreateModel(
            name="CommunicationLog",
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
                (
                    "comm_type",
                    models.CharField(
                        choices=[
                            ("email", "Email"),
                            ("call", "Call"),
                            ("meeting", "Meeting"),
                            ("note", "Note"),
                        ],
                        db_index=True, max_length=20,
                        help_text="Type of communication",
                    ),
                ),
                (
                    "direction",
                    models.CharField(
                        choices=[
                            ("inbound", "Inbound"),
                            ("outbound", "Outbound"),
                            ("internal", "Internal"),
                        ],
                        default="outbound", max_length=10,
                        help_text="Direction of the communication",
                    ),
                ),
                (
                    "subject",
                    models.CharField(
                        blank=True, max_length=500,
                        help_text="Subject line or brief title",
                    ),
                ),
                (
                    "content",
                    models.TextField(blank=True, help_text="Full body content"),
                ),
                (
                    "participant_ids",
                    models.JSONField(
                        blank=True, default=list,
                        help_text="List of participant user IDs",
                    ),
                ),
                (
                    "duration_minutes",
                    models.PositiveIntegerField(
                        blank=True, null=True,
                        help_text="Duration in minutes (for calls/meetings)",
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        blank=True, default=dict,
                        help_text="Extensible metadata (attachments, thread_id, etc.)",
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
                        auto_now=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "client",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="communications",
                        to="clients.client",
                        help_text="The client this communication is with",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="communications",
                        to="clients.project",
                        help_text="Optional linked project",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_communication_log",
                "verbose_name": "Communication Log",
                "verbose_name_plural": "Communication Logs",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="communicationlog",
            index=models.Index(
                fields=["tenant_id", "client", "-created_at"],
                name="voyager_comm_tenant_client_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="communicationlog",
            index=models.Index(
                fields=["tenant_id", "comm_type"],
                name="voyager_comm_tenant_type_idx",
            ),
        ),
        migrations.CreateModel(
            name="ClientPortal",
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
                    "slug",
                    models.SlugField(
                        max_length=255, unique=True,
                        help_text="URL-safe portal slug",
                    ),
                ),
                (
                    "branding",
                    models.JSONField(
                        blank=True, default=dict,
                        help_text="Branding config: colors, logo, fonts, custom CSS",
                    ),
                ),
                (
                    "custom_domain",
                    models.CharField(
                        blank=True, max_length=255,
                        help_text="Custom domain (e.g. portal.client.com)",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Whether the portal is currently active",
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
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="portal",
                        to="clients.client",
                        help_text="The client this portal belongs to",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_client_portal",
                "verbose_name": "Client Portal",
                "verbose_name_plural": "Client Portals",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="clientportal",
            index=models.Index(
                fields=["slug"],
                name="voyager_portal_slug_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="clientportal",
            index=models.Index(
                fields=["is_active"],
                name="voyager_portal_active_idx",
            ),
        ),
        migrations.CreateModel(
            name="ClientProfitability",
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
                (
                    "period_start",
                    models.DateField(help_text="Start of the reporting period"),
                ),
                (
                    "period_end",
                    models.DateField(help_text="End of the reporting period"),
                ),
                (
                    "revenue",
                    models.DecimalField(
                        decimal_places=2, default=0, max_digits=14,
                        help_text="Total revenue for the period",
                    ),
                ),
                (
                    "costs",
                    models.DecimalField(
                        decimal_places=2, default=0, max_digits=14,
                        help_text="Total costs for the period",
                    ),
                ),
                (
                    "margin_percent",
                    models.DecimalField(
                        decimal_places=2, default=0, max_digits=6,
                        help_text="Gross margin percentage",
                    ),
                ),
                (
                    "breakdown",
                    models.JSONField(
                        blank=True, default=dict,
                        help_text="Detailed breakdown of revenue and cost components",
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
                        related_name="profitability_records",
                        to="clients.client",
                        help_text="The client this profitability record is for",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_client_profitability",
                "verbose_name": "Client Profitability",
                "verbose_name_plural": "Client Profitabilities",
                "ordering": ["-period_end", "client"],
            },
        ),
        migrations.AddIndex(
            model_name="clientprofitability",
            index=models.Index(
                fields=["tenant_id", "client", "period_end"],
                name="voyager_profit_tenant_client_period_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="clientprofitability",
            index=models.Index(
                fields=["tenant_id", "period_start", "period_end"],
                name="voyager_profit_tenant_period_range_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="clientprofitability",
            constraint=models.UniqueConstraint(
                fields=["tenant_id", "client", "period_start", "period_end"],
                name="clients_profit_period_uniq",
            ),
        ),
    ]
