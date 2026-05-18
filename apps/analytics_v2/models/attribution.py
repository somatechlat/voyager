"""Attribution models for conversion path analysis.

Defines AttributionModel (configuration), ConversionPath (a single
conversion with its touchpoints), and Touchpoint (individual interaction
in a conversion journey).
"""

from __future__ import annotations

import uuid

from django.db import models

from apps.rbac.models import TenantScopedMixin


ATTRIBUTION_MODEL_CHOICES = [
    ("first_touch", "First Touch"),
    ("last_touch", "Last Touch"),
    ("linear", "Linear"),
    ("time_decay", "Time Decay"),
    ("position_based", "Position Based (U-Shaped)"),
    ("data_driven", "Data Driven (Markov Chain)"),
]

TOUCHPOINT_TYPE_CHOICES = [
    ("impression", "Impression"),
    ("click", "Click"),
    ("view", "View"),
    ("engagement", "Engagement"),
    ("visit", "Website Visit"),
    ("signup", "Sign Up"),
    ("download", "Download"),
    ("email_open", "Email Open"),
    ("email_click", "Email Click"),
    ("ad_click", "Ad Click"),
    ("organic_search", "Organic Search"),
    ("social_click", "Social Click"),
    ("referral", "Referral"),
    ("direct", "Direct"),
    ("conversion", "Conversion"),
]


class AttributionModel(TenantScopedMixin, models.Model):
    """Configuration for an attribution model applied to conversion data.

    Attributes:
        id: UUID primary key.
        tenant_id: Tenant scope identifier.
        name: Human-readable model name.
        model_type: The attribution algorithm (first_touch, last_touch, linear, etc.).
        config: JSON model-specific parameters (half_life, position weights, etc.).
        lookback_window_days: Maximum days before conversion to include touchpoints.
        is_default: Whether this is the default attribution model.
        created_by: User ID of the creator.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=255)
    model_type = models.CharField(
        max_length=32,
        choices=ATTRIBUTION_MODEL_CHOICES,
        default="last_touch",
    )
    config = models.JSONField(
        default=dict,
        help_text="Model-specific parameters: half_life, first_weight, last_weight",
    )
    lookback_window_days = models.PositiveIntegerField(default=30)
    is_default = models.BooleanField(default=False)
    created_by = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = "analytics_attribution_model"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "model_type"]),
            models.Index(fields=["tenant_id", "is_default"]),
            models.Index(fields=["tenant_id", "-created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="%(app_label)s_attr_tenant_name_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.model_type})"


class ConversionPath(TenantScopedMixin, models.Model):
    """A single conversion event with its complete touchpoint journey.

    Attributes:
        id: UUID primary key.
        tenant_id: Tenant scope identifier.
        conversion_id: External conversion identifier.
        user_id: The user/prospect who converted.
        conversion_value: Monetary value of the conversion.
        conversion_date: When the conversion occurred.
        currency: Currency code for the conversion value.
        channel: Primary channel that drove the conversion.
        campaign: Campaign associated with the conversion.
        attribution_model: Model used to calculate credits.
        total_touchpoints: Number of touchpoints in the journey.
        time_to_conversion_hours: Hours from first touchpoint to conversion.
        created_at: Creation timestamp.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=64, db_index=True)
    conversion_id = models.CharField(max_length=255, db_index=True)
    user_id = models.CharField(max_length=255, blank=True, db_index=True)
    conversion_value = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    conversion_date = models.DateTimeField(db_index=True)
    currency = models.CharField(max_length=3, default="USD")
    channel = models.CharField(max_length=64, blank=True, db_index=True)
    campaign = models.CharField(max_length=255, blank=True)
    attribution_model = models.ForeignKey(
        AttributionModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversion_paths",
    )
    total_touchpoints = models.PositiveIntegerField(default=0)
    time_to_conversion_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "analytics_conversion_path"
        ordering = ["-conversion_date"]
        indexes = [
            models.Index(fields=["tenant_id", "conversion_date"]),
            models.Index(fields=["tenant_id", "user_id"]),
            models.Index(fields=["tenant_id", "channel"]),
        ]

    def __str__(self) -> str:
        return f"Conversion {self.conversion_id} ({self.conversion_value} {self.currency})"


class Touchpoint(models.Model):
    """A single interaction in a conversion journey.

    Attributes:
        id: UUID primary key.
        conversion: Parent conversion path.
        sequence_order: Position in the journey (1 = first).
        touchpoint_type: Type of interaction (click, view, visit, etc.).
        channel: Marketing channel (social, email, paid, organic, etc.).
        platform: Specific platform (instagram, google, etc.).
        campaign: Campaign name.
        ad_group: Ad group or sub-campaign.
        creative: Creative/asset identifier.
        landing_page: URL of the landing page.
        referrer: Referring URL.
        device_type: Device category.
        geographic: Location data (city, country).
        timestamp: When the touchpoint occurred.
        credit: Attribution credit (0.0-1.0) assigned by the model.
        revenue_attributed: Revenue attributed to this touchpoint.
        time_since_previous_hours: Hours since the previous touchpoint.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversion = models.ForeignKey(
        ConversionPath,
        on_delete=models.CASCADE,
        related_name="touchpoints",
    )
    sequence_order = models.PositiveIntegerField(
        default=1,
        help_text="Position in the conversion journey (1 = first)",
    )
    touchpoint_type = models.CharField(
        max_length=32,
        choices=TOUCHPOINT_TYPE_CHOICES,
        default="click",
    )
    channel = models.CharField(max_length=64, blank=True, db_index=True)
    platform = models.CharField(max_length=64, blank=True, db_index=True)
    campaign = models.CharField(max_length=255, blank=True)
    ad_group = models.CharField(max_length=255, blank=True)
    creative = models.CharField(max_length=255, blank=True)
    landing_page = models.URLField(blank=True)
    referrer = models.URLField(blank=True)
    device_type = models.CharField(max_length=32, blank=True)
    geographic = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(db_index=True)
    credit = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0,
        help_text="Attribution credit (0.0 - 1.0)",
    )
    revenue_attributed = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        default=0,
    )
    time_since_previous_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "analytics_touchpoint"
        ordering = ["conversion", "sequence_order"]
        indexes = [
            models.Index(fields=["conversion", "sequence_order"]),
            models.Index(fields=["channel", "timestamp"]),
            models.Index(fields=["platform", "timestamp"]),
        ]

    def __str__(self) -> str:
        return f"Touchpoint {self.sequence_order} ({self.channel})"
