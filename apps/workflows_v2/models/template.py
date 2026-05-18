"""WorkflowTemplate model — pre-built, marketplace templates."""

from __future__ import annotations

from django.db import models


class WorkflowTemplate(models.Model):
    """A pre-built workflow template available in the marketplace.

    Templates are published workflow definitions that tenants can
    install and customize. They include metadata for discovery,
    configurable parameters, and required module dependencies.

    Attributes:
        id: Auto-incrementing primary key.
        name: Human-readable template name.
        description: Detailed template description.
        category: Template category for grouping.
        tags: JSON array of searchable tags.
        author: Template author identifier.
        version: Template version string (semver).
        rating: Average user rating (0.00-5.00).
        installs: Number of installations.
        workflow: The workflow definition JSON.
        configurable: JSON schema for customizable parameters.
        required_modules: List of required module names.
        is_public: Whether visible in marketplace.
        icon: Optional icon identifier.
        created_at: Timestamp.
        updated_at: Timestamp.
    """

    CATEGORY_CONTENT = "content"
    CATEGORY_APPROVAL = "approval"
    CATEGORY_NOTIFICATION = "notification"
    CATEGORY_INTEGRATION = "integration"
    CATEGORY_ANALYTICS = "analytics"
    CATEGORY_SOCIAL = "social"
    CATEGORY_EMAIL = "email"
    CATEGORY_CUSTOM = "custom"

    CATEGORY_CHOICES = [
        (CATEGORY_CONTENT, "Content"),
        (CATEGORY_APPROVAL, "Approval"),
        (CATEGORY_NOTIFICATION, "Notification"),
        (CATEGORY_INTEGRATION, "Integration"),
        (CATEGORY_ANALYTICS, "Analytics"),
        (CATEGORY_SOCIAL, "Social Media"),
        (CATEGORY_EMAIL, "Email Marketing"),
        (CATEGORY_CUSTOM, "Custom"),
    ]

    id = models.BigAutoField(primary_key=True, editable=False)
    name = models.CharField(
        max_length=255,
        help_text="Human-readable template name",
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed template description",
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_CUSTOM,
        db_index=True,
        help_text="Template category",
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Searchable tags",
    )
    author = models.CharField(
        max_length=100,
        help_text="Template author identifier",
    )
    version = models.CharField(
        max_length=20,
        default="1.0.0",
        help_text="Template version string (semver)",
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.0,
        help_text="Average user rating (0.00-5.00)",
    )
    installs = models.PositiveIntegerField(
        default=0,
        help_text="Number of installations",
    )
    workflow = models.JSONField(
        help_text="The workflow definition JSON",
    )
    configurable = models.JSONField(
        default=list,
        blank=True,
        help_text="JSON schema for customizable parameters",
    )
    required_modules = models.JSONField(
        default=list,
        blank=True,
        help_text="List of required module names",
    )
    is_public = models.BooleanField(
        default=True,
        help_text="Whether visible in marketplace",
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Icon identifier",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "voyager_workflow_template"
        verbose_name = "Workflow Template"
        verbose_name_plural = "Workflow Templates"
        ordering = ["-installs", "-rating", "name"]
        indexes = [
            models.Index(fields=["category", "is_public"]),
            models.Index(fields=["-rating"]),
            models.Index(fields=["-installs"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} v{self.version} by {self.author}"

    def record_install(self) -> None:
        """Increment install count."""
        self.installs += 1
        self.save(update_fields=["installs"])
