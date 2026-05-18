"""Dashboard and Widget models for configurable analytics dashboards.

A Dashboard is a collection of Widgets laid out in a grid. Each Widget
is a self-contained visualization (KPI card, chart, table, funnel, etc.)
backed by a metric query against the analytics data store.
"""

from __future__ import annotations

import uuid

from django.db import models

from apps.rbac.models import TenantScopedMixin


WIDGET_TYPE_CHOICES = [
    ("kpi_card", "KPI Card"),
    ("line_chart", "Line Chart"),
    ("bar_chart", "Bar Chart"),
    ("pie_chart", "Pie Chart"),
    ("heatmap", "Heatmap"),
    ("funnel", "Funnel"),
    ("table", "Table"),
    ("area_chart", "Area Chart"),
    ("scatter_plot", "Scatter Plot"),
    ("gauge", "Gauge"),
    ("scorecard", "Scorecard"),
    ("treemap", "Treemap"),
    ("cohort_table", "Cohort Table"),
    ("pivot_table", "Pivot Table"),
    ("comparison_bar", "Comparison Bar"),
    ("sparkline", "Sparkline"),
    ("top_list", "Top List"),
    ("metric_trend", "Metric Trend"),
]

PLATFORM_CHOICES = [
    ("instagram", "Instagram"),
    ("linkedin", "LinkedIn"),
    ("twitter", "Twitter/X"),
    ("tiktok", "TikTok"),
    ("facebook", "Facebook"),
    ("youtube", "YouTube"),
    ("pinterest", "Pinterest"),
    ("google_analytics", "Google Analytics"),
    ("google_ads", "Google Ads"),
    ("meta_ads", "Meta Ads"),
    ("linkedin_ads", "LinkedIn Ads"),
    ("sendgrid", "SendGrid"),
    ("gsc", "Google Search Console"),
    ("hubspot", "HubSpot"),
    ("stripe", "Stripe"),
    ("all", "All Platforms"),
]

METRIC_CHOICES = [
    ("impressions", "Impressions"),
    ("reach", "Reach"),
    ("engagement", "Engagement"),
    ("engagement_rate", "Engagement Rate"),
    ("clicks", "Clicks"),
    ("ctr", "Click-Through Rate"),
    ("cpc", "Cost Per Click"),
    ("cpm", "Cost Per Mille"),
    ("spend", "Spend"),
    ("conversions", "Conversions"),
    ("conversion_rate", "Conversion Rate"),
    ("revenue", "Revenue"),
    ("roas", "ROAS"),
    ("roi", "ROI"),
    ("followers", "Followers"),
    ("follower_growth", "Follower Growth"),
    ("video_views", "Video Views"),
    ("video_completion_rate", "Video Completion Rate"),
    ("saves", "Saves"),
    ("shares", "Shares"),
    ("comments", "Comments"),
    ("likes", "Likes"),
    ("delivered", "Emails Delivered"),
    ("open_rate", "Open Rate"),
    ("click_rate", "Click Rate"),
    ("bounce_rate", "Bounce Rate"),
    ("unsubscribe_rate", "Unsubscribe Rate"),
    ("organic_sessions", "Organic Sessions"),
    ("organic_clicks", "Organic Clicks"),
    ("keyword_rankings", "Keyword Rankings"),
    ("domain_authority", "Domain Authority"),
    ("backlinks", "Backlinks"),
    ("mrr", "MRR"),
    ("churn_rate", "Churn Rate"),
    ("ltv", "LTV"),
    ("cac", "CAC"),
    ("frequency", "Frequency"),
    ("cost_per_conversion", "Cost Per Conversion"),
]

COMPARISON_CHOICES = [
    ("none", "No Comparison"),
    ("previous_period", "Previous Period"),
    ("year_over_year", "Year over Year"),
    ("against_target", "Against Target"),
    ("benchmark", "Benchmark"),
]


class Dashboard(TenantScopedMixin, models.Model):
    """A configurable analytics dashboard composed of widgets.

    Attributes:
        id: UUID primary key.
        tenant_id: Tenant scope identifier.
        name: Human-readable dashboard name.
        description: Optional longer description.
        layout: JSON grid layout configuration (rows, cols, widget positions).
        filters: JSON default filters applied to all widgets.
        is_default: Whether this is the default dashboard for the tenant.
        is_shared: Whether the dashboard is shared with the team.
        shared_with: List of user IDs with access.
        created_by: User ID of the dashboard creator.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    layout = models.JSONField(default=dict, help_text="Grid layout configuration")
    filters = models.JSONField(default=dict, blank=True, help_text="Default dashboard filters")
    is_default = models.BooleanField(default=False)
    is_shared = models.BooleanField(default=False)
    shared_with = models.JSONField(default=list, blank=True, help_text="User IDs with access")
    created_by = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = "analytics_dashboard"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "-created_at"]),
            models.Index(fields=["tenant_id", "is_default"]),
            models.Index(fields=["tenant_id", "created_by"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="%(app_label)s_dash_tenant_name_uniq",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def to_config(self) -> dict:
        """Serialize dashboard configuration for the widget engine."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "layout": self.layout,
            "filters": self.filters,
            "is_default": self.is_default,
            "widgets": [w.to_config() for w in self.widgets.all()],
        }


class Widget(models.Model):
    """A single visualization widget within a dashboard.

    Widgets are self-contained visualizations backed by a metric query.
    The widget_type field determines the renderer used by the frontend.

    Attributes:
        id: UUID primary key.
        dashboard: Parent dashboard.
        widget_type: Visualization type (chart, table, KPI, etc.).
        title: Widget display title.
        subtitle: Optional subtitle.
        position: JSON grid position (x, y, w, h).
        config: Full widget configuration (metrics, dimensions, filters).
        refresh_interval: Auto-refresh interval in seconds (0 = manual).
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dashboard = models.ForeignKey(
        Dashboard,
        on_delete=models.CASCADE,
        related_name="widgets",
    )
    widget_type = models.CharField(max_length=32, choices=WIDGET_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    position = models.JSONField(
        default=dict,
        help_text="Grid position: {x, y, w, h}",
    )
    config = models.JSONField(
        default=dict,
        help_text="Widget configuration: metrics, dimensions, filters, comparison",
    )
    refresh_interval = models.PositiveIntegerField(
        default=0,
        help_text="Auto-refresh interval in seconds; 0 = manual refresh",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_widget"
        ordering = ["dashboard", "-updated_at"]
        indexes = [
            models.Index(fields=["dashboard", "widget_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.widget_type})"

    def to_config(self) -> dict:
        """Serialize widget configuration for the rendering engine."""
        return {
            "id": str(self.id),
            "type": self.widget_type,
            "title": self.title,
            "subtitle": self.subtitle,
            "position": self.position,
            "config": self.config,
            "refresh_interval": self.refresh_interval,
        }
