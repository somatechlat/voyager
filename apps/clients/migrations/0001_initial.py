# Generated initial migration for clients


from django.db import migrations, models


class BudgetType(models.TextChoices):
    FIXED = "fixed", "Fixed Price"
    HOURLY = "hourly", "Hourly"
    RETAINER = "retainer", "Retainer"
    HYBRID = "hybrid", "Hybrid"


class Status(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"
    PAUSED = "paused", "Paused"
    ONBOARDING = "onboarding", "Onboarding"
    CHURNED = "churned", "Churned"


class Tier(models.TextChoices):
    BASIC = "basic", "Basic"
    PRO = "pro", "Pro"
    ENTERPRISE = "enterprise", "Enterprise"


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Client",
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
                ("name", models.CharField(max_length=255, help_text="Client company name")),
                ("slug", models.SlugField(max_length=255, help_text="URL-safe unique identifier")),
                (
                    "industry",
                    models.CharField(
                        max_length=100,
                        blank=True,
                        help_text="Industry sector (e.g. 'Technology', 'Healthcare')",
                    ),
                ),
                ("website", models.URLField(blank=True, help_text="Client website URL")),
                ("logo_url", models.URLField(blank=True, help_text="URL to the client logo image")),
                (
                    "contact_name",
                    models.CharField(
                        max_length=255,
                        blank=True,
                        help_text="Primary contact person's full name",
                    ),
                ),
                (
                    "contact_email",
                    models.EmailField(
                        blank=True,
                        help_text="Primary contact email address",
                    ),
                ),
                (
                    "contact_phone",
                    models.CharField(
                        max_length=50,
                        blank=True,
                        help_text="Primary contact phone number",
                    ),
                ),
                ("address", models.TextField(blank=True, help_text="Physical office address")),
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
                        max_length=100,
                        blank=True,
                        help_text="Tax or VAT identification number",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=Status.choices,
                        default=Status.ACTIVE,
                        db_index=True,
                        help_text="Current client lifecycle status",
                    ),
                ),
                (
                    "tier",
                    models.CharField(
                        max_length=20,
                        choices=Tier.choices,
                        default=Tier.BASIC,
                        help_text="Service tier subscription level",
                    ),
                ),
                (
                    "settings",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Client-specific configuration settings",
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Extensible metadata for custom attributes",
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
                "db_table": "voyager_client",
                "verbose_name": "Client",
                "verbose_name_plural": "Clients",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "status"]),
                    models.Index(fields=["tenant_id", "tier"]),
                    models.Index(fields=["tenant_id", "slug"]),
                    models.Index(fields=["tenant_id", "-created_at"]),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["tenant_id", "slug"], name="clients_client_tenant_slug_uniq"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="ClientContact",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "client",
                    models.ForeignKey(
                        Client,
                        on_delete=models.CASCADE,
                        related_name="contacts",
                        help_text="The parent client this contact belongs to",
                    ),
                ),
                ("name", models.CharField(max_length=255, help_text="Contact person's full name")),
                ("email", models.EmailField(help_text="Contact email address")),
                (
                    "phone",
                    models.CharField(
                        max_length=50,
                        blank=True,
                        help_text="Contact phone number",
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        max_length=100,
                        blank=True,
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
            ],
            options={
                "db_table": "voyager_client_contact",
                "verbose_name": "Client Contact",
                "verbose_name_plural": "Client Contacts",
                "ordering": ["-is_primary", "name"],
                "indexes": [
                    models.Index(fields=["client", "is_primary"]),
                    models.Index(fields=["client", "email"]),
                ],
            },
        ),
        migrations.CreateModel(
            name="Project",
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
                    "client",
                    models.ForeignKey(
                        Client,
                        on_delete=models.CASCADE,
                        related_name="projects",
                        help_text="The client this project belongs to",
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
                        max_length=20,
                        choices=Status.choices,
                        default=Status.PLANNING,
                        db_index=True,
                        help_text="Current project status",
                    ),
                ),
                (
                    "start_date",
                    models.DateField(null=True, blank=True, help_text="Project start date"),
                ),
                (
                    "end_date",
                    models.DateField(
                        null=True,
                        blank=True,
                        help_text="Project end date (estimated or actual)",
                    ),
                ),
                (
                    "budget_amount",
                    models.DecimalField(
                        max_digits=14,
                        decimal_places=2,
                        null=True,
                        blank=True,
                        help_text="Allocated budget amount",
                    ),
                ),
                (
                    "budget_type",
                    models.CharField(
                        max_length=20,
                        choices=BudgetType.choices,
                        default=BudgetType.FIXED,
                        help_text="How the project is billed",
                    ),
                ),
                (
                    "manager_id",
                    models.CharField(
                        max_length=256,
                        blank=True,
                        db_index=True,
                        help_text="User ID of the project manager",
                    ),
                ),
                (
                    "team_ids",
                    models.JSONField(
                        default=list,
                        blank=True,
                        help_text="List of team member user IDs",
                    ),
                ),
                (
                    "settings",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Project-specific configuration",
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
                "db_table": "voyager_project",
                "verbose_name": "Project",
                "verbose_name_plural": "Projects",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "status"]),
                    models.Index(fields=["tenant_id", "client", "status"]),
                    models.Index(fields=["tenant_id", "manager_id"]),
                    models.Index(fields=["tenant_id", "-created_at"]),
                ],
            },
        ),
    ]
