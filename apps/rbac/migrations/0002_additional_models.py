# Generated initial migration for rbac


from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [("rbac", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="RoleAssignment",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "user_id",
                    models.CharField(
                        max_length=256,
                        db_index=True,
                        help_text="Keycloak subject identifier (UUID string) of the user",
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        Role,
                        on_delete=models.CASCADE,
                        related_name="assignments",
                        help_text="The role being assigned to the user",
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
                    "workspace_id",
                    models.CharField(
                        max_length=128,
                        blank=True,
                        db_index=True,
                        help_text="Optional workspace-scoped assignment",
                    ),
                ),
                (
                    "granted_by",
                    models.CharField(
                        max_length=256,
                        help_text="User ID of the administrator who granted this assignment",
                    ),
                ),
                (
                    "granted_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when the assignment was created",
                    ),
                ),
                (
                    "expires_at",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        help_text="Optional expiration timestamp for time-bounded access",
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
                "db_table": "voyager_role_assignment",
                "verbose_name": "Role Assignment",
                "verbose_name_plural": "Role Assignments",
                "ordering": ["-granted_at"],
                "indexes": [
                    models.Index(fields=["user_id", "tenant_id"]),
                    models.Index(fields=["tenant_id", "role"]),
                    models.Index(fields=["tenant_id", "workspace_id"]),
                    models.Index(fields=["expires_at"]),
                ],
                "unique_together": [["user_id", "role", "tenant_id", "workspace_id"]],
            },
        ),
        migrations.CreateModel(
            name="PermissionAssignment",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "role",
                    models.ForeignKey(
                        Role,
                        on_delete=models.CASCADE,
                        related_name="permission_assignments",
                        help_text="The role that receives this permission",
                    ),
                ),
                (
                    "permission",
                    models.ForeignKey(
                        Permission,
                        on_delete=models.CASCADE,
                        related_name="role_assignments",
                        help_text="The permission being assigned to the role",
                    ),
                ),
                (
                    "conditions",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Optional row-level filter conditions evaluated at runtime",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_permission_assignment",
                "verbose_name": "Permission Assignment",
                "verbose_name_plural": "Permission Assignments",
                "ordering": ["role", "permission"],
                "indexes": [models.Index(fields=["role", "permission"])],
                "unique_together": [["role", "permission"]],
            },
        ),
        migrations.CreateModel(
            name="Workspace",
            fields=[
                ("id", models.BigAutoField(primary_key=True, editable=False)),
                (
                    "name",
                    models.CharField(max_length=255, help_text="Human-readable workspace name"),
                ),
                ("slug", models.SlugField(unique=True, help_text="URL-safe unique identifier")),
                (
                    "tenant_id",
                    models.CharField(
                        max_length=128,
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Optional longer explanation of the workspace",
                    ),
                ),
                (
                    "settings",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Workspace-specific configuration (e.g. theme, quotas)",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Whether the workspace is currently active",
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Optional metadata for extensibility",
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
                "db_table": "voyager_workspace",
                "verbose_name": "Workspace",
                "verbose_name_plural": "Workspaces",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant_id", "slug"]),
                    models.Index(fields=["tenant_id", "is_active"]),
                    models.Index(fields=["tenant_id", "-created_at"]),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=["tenant_id", "slug"],
                        name="%(app_label)s_workspace_tenant_slug_uniq",
                    )
                ],
            },
        ),
    ]
