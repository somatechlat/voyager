# Generated initial migration for rbac


from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Role",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "name",
                    models.CharField(
                        max_length=128,
                        unique=True,
                        help_text="Unique human-readable role name (e.g. 'Content Manager')",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Optional longer explanation of the role's purpose",
                    ),
                ),
                (
                    "parent",
                    models.ForeignKey(
                        to="self",
                        null=True,
                        blank=True,
                        on_delete=models.SET_NULL,
                        related_name="children",
                        help_text="Optional parent role for permission inheritance",
                    ),
                ),
                (
                    "permissions",
                    models.JSONField(
                        default=list,
                        help_text="List of permission codenames granted by this role",
                    ),
                ),
                (
                    "is_system",
                    models.BooleanField(
                        default=False,
                        help_text="Whether this role is protected from deletion",
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
                "db_table": "voyager_role",
                "verbose_name": "Role",
                "verbose_name_plural": "Roles",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "name"]),
                    models.Index(fields=["tenant_id", "-created_at"]),
                    models.Index(fields=["parent", "tenant_id"]),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["tenant_id", "name"], name="%(app_label)s_role_tenant_name_uniq"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="Permission",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "codename",
                    models.CharField(
                        max_length=128,
                        unique=True,
                        help_text="Composite identifier in the form 'module:action'",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=255,
                        help_text="Human-readable permission name (e.g. 'Create Content')",
                    ),
                ),
                (
                    "module",
                    models.CharField(
                        max_length=64,
                        db_index=True,
                        help_text="Application module this permission belongs to (e.g. 'content_creation')",
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        max_length=64,
                        help_text="The CRUD action: read, write, delete, or execute",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Optional longer explanation of the permission",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_permission",
                "verbose_name": "Permission",
                "verbose_name_plural": "Permissions",
                "ordering": ["module", "codename"],
                "indexes": [models.Index(fields=["module", "action"])],
            },
        ),
    ]
