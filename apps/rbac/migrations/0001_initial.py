"""Initial migration for the RBAC app.

Creates Role, Permission, RoleAssignment, PermissionAssignment, and Workspace
models with full indexes, constraints, and foreign key relationships.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Initial migration that bootstraps the RBAC schema."""

    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        # ── Permission ────────────────────────────────────────────────────
        migrations.CreateModel(
            name="Permission",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
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
            },
        ),
        migrations.AddIndex(
            model_name="permission",
            index=models.Index(
                fields=["module", "action"],
                name="voyager_permission_module_action_idx",
            ),
        ),
        # ── Role ──────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="Role",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=128,
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
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="children",
                        to="rbac.role",
                        help_text="Optional parent role for permission inheritance",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_role",
                "verbose_name": "Role",
                "verbose_name_plural": "Roles",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="role",
            index=models.Index(
                fields=["tenant_id", "name"],
                name="voyager_role_tenant_name_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="role",
            index=models.Index(
                fields=["tenant_id", "-created_at"],
                name="voyager_role_tenant_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="role",
            index=models.Index(
                fields=["parent", "tenant_id"],
                name="voyager_role_parent_tenant_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="role",
            constraint=models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="rbac_role_tenant_name_uniq",
            ),
        ),
        # ── RoleAssignment ────────────────────────────────────────────────
        migrations.CreateModel(
            name="RoleAssignment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "user_id",
                    models.CharField(
                        max_length=256,
                        db_index=True,
                        help_text="Keycloak subject identifier (UUID string) of the user",
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
                        blank=True,
                        null=True,
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
                (
                    "role",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignments",
                        to="rbac.role",
                        help_text="The role being assigned to the user",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_role_assignment",
                "verbose_name": "Role Assignment",
                "verbose_name_plural": "Role Assignments",
                "ordering": ["-granted_at"],
            },
        ),
        migrations.AlterUniqueTogether(
            name="roleassignment",
            unique_together={("user_id", "role", "tenant_id", "workspace_id")},
        ),
        migrations.AddIndex(
            model_name="roleassignment",
            index=models.Index(
                fields=["user_id", "tenant_id"],
                name="voyager_ra_user_tenant_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="roleassignment",
            index=models.Index(
                fields=["tenant_id", "role"],
                name="voyager_ra_tenant_role_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="roleassignment",
            index=models.Index(
                fields=["tenant_id", "workspace_id"],
                name="voyager_ra_tenant_ws_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="roleassignment",
            index=models.Index(
                fields=["expires_at"],
                name="voyager_ra_expires_idx",
            ),
        ),
        # ── PermissionAssignment ──────────────────────────────────────────
        migrations.CreateModel(
            name="PermissionAssignment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "conditions",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Optional row-level filter conditions evaluated at runtime",
                    ),
                ),
                (
                    "permission",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="role_assignments",
                        to="rbac.permission",
                        help_text="The permission being assigned to the role",
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="permission_assignments",
                        to="rbac.role",
                        help_text="The role that receives this permission",
                    ),
                ),
            ],
            options={
                "db_table": "voyager_permission_assignment",
                "verbose_name": "Permission Assignment",
                "verbose_name_plural": "Permission Assignments",
                "ordering": ["role", "permission"],
            },
        ),
        migrations.AlterUniqueTogether(
            name="permissionassignment",
            unique_together={("role", "permission")},
        ),
        migrations.AddIndex(
            model_name="permissionassignment",
            index=models.Index(
                fields=["role", "permission"],
                name="voyager_pa_role_perm_idx",
            ),
        ),
        # ── Workspace ─────────────────────────────────────────────────────
        migrations.CreateModel(
            name="Workspace",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=255,
                        help_text="Human-readable workspace name",
                    ),
                ),
                (
                    "slug",
                    models.SlugField(
                        unique=True,
                        help_text="URL-safe unique identifier",
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
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Optional longer explanation of the workspace",
                    ),
                ),
                (
                    "settings",
                    models.JSONField(
                        blank=True,
                        default=dict,
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
                        blank=True,
                        default=dict,
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
            },
        ),
        migrations.AddIndex(
            model_name="workspace",
            index=models.Index(
                fields=["tenant_id", "slug"],
                name="voyager_ws_tenant_slug_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="workspace",
            index=models.Index(
                fields=["tenant_id", "is_active"],
                name="voyager_ws_tenant_active_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="workspace",
            index=models.Index(
                fields=["tenant_id", "-created_at"],
                name="voyager_ws_tenant_created_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="workspace",
            constraint=models.UniqueConstraint(
                fields=["tenant_id", "slug"],
                name="rbac_workspace_tenant_slug_uniq",
            ),
        ),
    ]
