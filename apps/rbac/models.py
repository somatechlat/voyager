"""RBAC models for role-based access control.

Defines Role, Permission, RoleAssignment, PermissionAssignment, and Workspace
models that provide tenant-scoped authorization with workspace-level isolation.
All models inherit from Voyant's abstract base classes (UUIDModel, TimeStampedModel)
for consistent primary keys, timestamps, and multi-tenancy support.
"""

from __future__ import annotations

from django.db import models


class Role(models.Model):
    """A role defines a set of permissions that can be assigned to users.

    Roles support hierarchical inheritance via the ``parent`` self-referential
    foreign key. A role inherits all permissions from its parent chain.
    System roles are protected from deletion to prevent accidental lockouts.

    Attributes:
        id: Auto-incrementing primary key (BigAutoField).
        name: Unique human-readable role name (e.g. "Content Manager").
        description: Optional longer explanation of the role's purpose.
        parent: Optional parent role for permission inheritance.
        permissions: JSON list of permission codenames granted directly.
        is_system: Whether the role is protected from deletion.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    name = models.CharField(
        max_length=128,
        unique=True,
        help_text="Unique human-readable role name (e.g. 'Content Manager')",
    )
    description = models.TextField(
        blank=True,
        help_text="Optional longer explanation of the role's purpose",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
        help_text="Optional parent role for permission inheritance",
    )
    permissions = models.JSONField(
        default=list,
        help_text="List of permission codenames granted by this role",
    )
    is_system = models.BooleanField(
        default=False,
        help_text="Whether this role is protected from deletion",
    )
    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
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
        db_table = "voyager_role"
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "name"]),
            models.Index(fields=["tenant_id", "-created_at"]),
            models.Index(fields=["parent", "tenant_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="%(app_label)s_role_tenant_name_uniq",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def get_all_permissions(self) -> list[str]:
        """Return the effective permission set including inherited permissions.

        Walks the parent chain recursively and merges all permission
codenames into a deduplicated list.

        Returns:
            List of permission codenames effective for this role.
        """
        perms: set[str] = set(self.permissions or [])
        if self.parent_id:
            try:
                perms.update(self.parent.get_all_permissions())
            except Role.DoesNotExist:
                pass
        return sorted(perms)

    def has_permission(self, codename: str) -> bool:
        """Check whether this role (or its parent chain) grants a permission.

        Args:
            codename: The permission codename to check (e.g. "content_creation:write").

        Returns:
            ``True`` if the permission is granted, ``False`` otherwise.
        """
        effective: list[str] = self.get_all_permissions()
        return codename in effective


class Permission(models.Model):
    """A permission defines an authorization boundary within a module.

    Permissions are identified by a composite codename of the form
    ``module:action`` (e.g. ``content_creation:write``) and represent
    the finest granularity of the access control system.

    Attributes:
        id: Auto-incrementing primary key (BigAutoField).
        codename: Unique composite identifier ``module:action``.
        name: Human-readable permission name (e.g. "Create Content").
        module: Application module this permission belongs to.
        action: The CRUD action (read, write, delete, execute).
        description: Optional longer explanation of the permission.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    codename = models.CharField(
        max_length=128,
        unique=True,
        help_text="Composite identifier in the form 'module:action'",
    )
    name = models.CharField(
        max_length=255,
        help_text="Human-readable permission name (e.g. 'Create Content')",
    )
    module = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Application module this permission belongs to (e.g. 'content_creation')",
    )
    action = models.CharField(
        max_length=64,
        help_text="The CRUD action: read, write, delete, or execute",
    )
    description = models.TextField(
        blank=True,
        help_text="Optional longer explanation of the permission",
    )

    class Meta:
        db_table = "voyager_permission"
        verbose_name = "Permission"
        verbose_name_plural = "Permissions"
        ordering = ["module", "codename"]
        indexes = [
            models.Index(fields=["module", "action"]),
        ]

    def __str__(self) -> str:
        return f"{self.codename} ({self.name})"


class RoleAssignment(models.Model):
    """A role assignment binds a user to a role within a tenant/workspace scope.

    Role assignments are the mechanism by which users receive permissions.
    A user may have multiple role assignments. Assignments can optionally
    expire (time-bounded access) and be scoped to a specific workspace.

    Attributes:
        id: Auto-incrementing primary key (BigAutoField).
        user_id: Keycloak subject identifier (UUID string) of the user.
        role: The role being assigned.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        workspace_id: Optional workspace-scoped assignment.
        granted_by: User ID of the administrator who granted this assignment.
        granted_at: Timestamp when the assignment was created.
        expires_at: Optional expiration timestamp for time-bounded access.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    user_id = models.CharField(
        max_length=256,
        db_index=True,
        help_text="Keycloak subject identifier (UUID string) of the user",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="assignments",
        help_text="The role being assigned to the user",
    )
    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    workspace_id = models.CharField(
        max_length=128,
        blank=True,
        db_index=True,
        help_text="Optional workspace-scoped assignment",
    )
    granted_by = models.CharField(
        max_length=256,
        help_text="User ID of the administrator who granted this assignment",
    )
    granted_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the assignment was created",
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional expiration timestamp for time-bounded access",
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
        db_table = "voyager_role_assignment"
        verbose_name = "Role Assignment"
        verbose_name_plural = "Role Assignments"
        ordering = ["-granted_at"]
        unique_together = [["user_id", "role", "tenant_id", "workspace_id"]]
        indexes = [
            models.Index(fields=["user_id", "tenant_id"]),
            models.Index(fields=["tenant_id", "role"]),
            models.Index(fields=["tenant_id", "workspace_id"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        scope = f"/{self.workspace_id}" if self.workspace_id else ""
        return f"{self.user_id} -> {self.role.name} @ {self.tenant_id}{scope}"

    def is_expired(self) -> bool:
        """Check whether this assignment has expired.

        Returns:
            ``True`` if ``expires_at`` is set and in the past,
            ``False`` otherwise (including when no expiration is set).
        """
        if self.expires_at is None:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at


class PermissionAssignment(models.Model):
    """A permission assignment links a role to a permission with optional conditions.

    This model implements fine-grained access control by allowing row-level
    conditions (e.g. ``{"status": "draft"}``) to be attached to a permission.
    The conditions JSON is evaluated at runtime by the RBAC middleware.

    Attributes:
        id: Auto-incrementing primary key (BigAutoField).
        role: The role that receives this permission.
        permission: The permission being assigned.
        conditions: Optional row-level filter conditions as JSON.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="permission_assignments",
        help_text="The role that receives this permission",
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="role_assignments",
        help_text="The permission being assigned to the role",
    )
    conditions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Optional row-level filter conditions evaluated at runtime",
    )

    class Meta:
        db_table = "voyager_permission_assignment"
        verbose_name = "Permission Assignment"
        verbose_name_plural = "Permission Assignments"
        ordering = ["role", "permission"]
        unique_together = [["role", "permission"]]
        indexes = [
            models.Index(fields=["role", "permission"]),
        ]

    def __str__(self) -> str:
        return f"{self.role.name} -> {self.permission.codename}"


class Workspace(models.Model):
    """A workspace is a logical subdivision of a tenant for resource isolation.

    Workspaces allow teams within the same tenant to operate independently
    with separate settings, roles, and resource boundaries. Each workspace
    is identified by a unique slug and scoped to a single tenant.

    Attributes:
        id: Auto-incrementing primary key (BigAutoField).
        name: Human-readable workspace name.
        slug: URL-safe unique identifier.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        description: Optional longer explanation of the workspace.
        settings: JSON workspace-specific configuration.
        is_active: Whether the workspace is currently active.
        metadata: Optional JSON metadata for extensibility.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    name = models.CharField(
        max_length=255,
        help_text="Human-readable workspace name",
    )
    slug = models.SlugField(
        unique=True,
        help_text="URL-safe unique identifier",
    )
    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    description = models.TextField(
        blank=True,
        help_text="Optional longer explanation of the workspace",
    )
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Workspace-specific configuration (e.g. theme, quotas)",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the workspace is currently active",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Optional metadata for extensibility",
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
        db_table = "voyager_workspace"
        verbose_name = "Workspace"
        verbose_name_plural = "Workspaces"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "slug"]),
            models.Index(fields=["tenant_id", "is_active"]),
            models.Index(fields=["tenant_id", "-created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "slug"],
                name="%(app_label)s_workspace_tenant_slug_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"
