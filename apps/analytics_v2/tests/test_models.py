"""Tests for Analytics v2 models: Dashboard, Widget, ReportTemplate, ReportSchedule."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.analytics_v2.models import Dashboard, ReportSchedule, ReportTemplate, Widget

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tenant_id() -> str:
    """Return a consistent tenant ID for tests."""
    return "test-tenant-001"


@pytest.fixture
def dashboard(tenant_id: str) -> Dashboard:
    """Create and return a Dashboard instance."""
    return Dashboard.objects.create(
        tenant_id=tenant_id,
        name="Social Media Overview",
        description="Key metrics for social media performance",
        layout={"rows": 3, "cols": 4, "widgets": []},
        filters={"date_range": "last_30_days", "platform": "all"},
        is_default=True,
        is_shared=True,
        shared_with=["user-001", "user-002"],
        created_by="user-001",
    )


@pytest.fixture
def widget(dashboard: Dashboard) -> Widget:
    """Create and return a Widget instance linked to a dashboard."""
    return Widget.objects.create(
        dashboard=dashboard,
        widget_type="kpi_card",
        title="Total Impressions",
        subtitle="Last 30 days",
        position={"x": 0, "y": 0, "w": 2, "h": 1},
        config={
            "metric": "impressions",
            "platform": "all",
            "comparison": "previous_period",
        },
        refresh_interval=300,
    )


@pytest.fixture
def report_template(tenant_id: str) -> ReportTemplate:
    """Create and return a ReportTemplate instance."""
    return ReportTemplate.objects.create(
        tenant_id=tenant_id,
        name="Monthly Engagement Report",
        description="Standard monthly engagement metrics",
        category="engagement",
        config={
            "metrics": ["engagement_rate", "reach", "impressions"],
            "dimensions": ["platform", "date"],
            "filters": {"date_range": "last_30_days"},
            "visualizations": ["line_chart", "table"],
        },
        format="pdf",
        is_favorite=True,
        created_by="user-001",
    )


# ---------------------------------------------------------------------------
# Dashboard tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dashboard_creation(dashboard: Dashboard) -> None:
    """Dashboard can be created with all required fields."""
    assert dashboard.id is not None
    assert isinstance(dashboard.id, uuid.UUID)
    assert dashboard.name == "Social Media Overview"
    assert dashboard.tenant_id == "test-tenant-001"
    assert dashboard.is_default is True
    assert dashboard.is_shared is True
    assert dashboard.created_by == "user-001"


@pytest.mark.django_db
def test_dashboard_str(dashboard: Dashboard) -> None:
    """String representation returns the name."""
    assert str(dashboard) == "Social Media Overview"


@pytest.mark.django_db
def test_dashboard_defaults(tenant_id: str) -> None:
    """Dashboard fields have correct defaults."""
    db = Dashboard.objects.create(
        tenant_id=tenant_id,
        name="Default Dashboard",
        created_by="user-001",
    )
    assert db.layout == {}
    assert db.filters == {}
    assert db.is_default is False
    assert db.is_shared is False
    assert db.shared_with == []
    assert db.description == ""


@pytest.mark.django_db
def test_dashboard_unique_name_per_tenant(tenant_id: str) -> None:
    """Duplicate dashboard name within same tenant raises IntegrityError."""
    Dashboard.objects.create(
        tenant_id=tenant_id,
        name="Unique Dash",
        created_by="user-001",
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Dashboard.objects.create(
                tenant_id=tenant_id,
                name="Unique Dash",
                created_by="user-002",
            )


@pytest.mark.django_db
def test_dashboard_same_name_different_tenants() -> None:
    """Same dashboard name in different tenants is allowed."""
    d1 = Dashboard.objects.create(
        tenant_id="tenant-a",
        name="Shared Dash",
        created_by="user-001",
    )
    d2 = Dashboard.objects.create(
        tenant_id="tenant-b",
        name="Shared Dash",
        created_by="user-001",
    )
    assert d1.id is not None
    assert d2.id is not None


@pytest.mark.django_db
def test_dashboard_to_config(dashboard: Dashboard, widget: Widget) -> None:
    """to_config serializes dashboard with widgets."""
    config = dashboard.to_config()
    assert config["id"] == str(dashboard.id)
    assert config["name"] == "Social Media Overview"
    assert config["is_default"] is True
    assert config["layout"] == {"rows": 3, "cols": 4, "widgets": []}
    assert config["filters"] == {"date_range": "last_30_days", "platform": "all"}
    assert len(config["widgets"]) == 1
    assert config["widgets"][0]["id"] == str(widget.id)


@pytest.mark.django_db
def test_dashboard_to_config_empty(tenant_id: str) -> None:
    """to_config handles dashboard with no widgets."""
    db = Dashboard.objects.create(
        tenant_id=tenant_id,
        name="Empty Dashboard",
        created_by="user-001",
    )
    config = db.to_config()
    assert config["widgets"] == []


@pytest.mark.django_db
def test_dashboard_timestamps(dashboard: Dashboard) -> None:
    """Dashboard has created_at and updated_at timestamps."""
    assert dashboard.created_at is not None
    assert dashboard.updated_at is not None


# ---------------------------------------------------------------------------
# Widget tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_widget_creation(widget: Widget) -> None:
    """Widget can be created linked to a dashboard."""
    assert widget.id is not None
    assert isinstance(widget.id, uuid.UUID)
    assert widget.dashboard == widget.dashboard  # valid FK
    assert widget.widget_type == "kpi_card"
    assert widget.title == "Total Impressions"
    assert widget.subtitle == "Last 30 days"
    assert widget.refresh_interval == 300


@pytest.mark.django_db
def test_widget_str(widget: Widget) -> None:
    """String representation includes title and widget type."""
    assert str(widget) == "Total Impressions (kpi_card)"


@pytest.mark.django_db
def test_widget_defaults(dashboard: Dashboard) -> None:
    """Widget fields have correct defaults."""
    w = Widget.objects.create(
        dashboard=dashboard,
        widget_type="line_chart",
        title="Follower Growth",
    )
    assert w.position == {}
    assert w.config == {}
    assert w.refresh_interval == 0
    assert w.subtitle == ""


@pytest.mark.django_db
def test_widget_to_config(widget: Widget) -> None:
    """to_config serializes widget configuration."""
    config = widget.to_config()
    assert config["id"] == str(widget.id)
    assert config["type"] == "kpi_card"
    assert config["title"] == "Total Impressions"
    assert config["subtitle"] == "Last 30 days"
    assert config["position"] == {"x": 0, "y": 0, "w": 2, "h": 1}
    assert config["config"] == {
        "metric": "impressions",
        "platform": "all",
        "comparison": "previous_period",
    }
    assert config["refresh_interval"] == 300


@pytest.mark.django_db
def test_widget_related_to_dashboard(dashboard: Dashboard, widget: Widget) -> None:
    """Widget is linked to Dashboard via foreign key."""
    assert widget.dashboard == dashboard
    assert dashboard.widgets.count() == 1
    assert dashboard.widgets.first() == widget


@pytest.mark.django_db
def test_widget_cascade_delete(dashboard: Dashboard, widget: Widget) -> None:
    """Widget is deleted when parent Dashboard is deleted."""
    dashboard.delete()
    assert Widget.objects.filter(id=widget.id).count() == 0


@pytest.mark.django_db
def test_widget_multiple_widgets(dashboard: Dashboard) -> None:
    """A dashboard can have multiple widgets."""
    for i in range(5):
        Widget.objects.create(
            dashboard=dashboard,
            widget_type="kpi_card",
            title=f"Widget {i}",
        )
    assert dashboard.widgets.count() == 5


# ---------------------------------------------------------------------------
# ReportTemplate tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_report_template_creation(report_template: ReportTemplate) -> None:
    """ReportTemplate can be created with all required fields."""
    assert report_template.id is not None
    assert isinstance(report_template.id, uuid.UUID)
    assert report_template.name == "Monthly Engagement Report"
    assert report_template.tenant_id == "test-tenant-001"
    assert report_template.category == "engagement"
    assert report_template.format == "pdf"
    assert report_template.is_favorite is True


@pytest.mark.django_db
def test_report_template_str(report_template: ReportTemplate) -> None:
    """String representation returns the name."""
    assert str(report_template) == "Monthly Engagement Report"


@pytest.mark.django_db
def test_report_template_defaults(tenant_id: str) -> None:
    """ReportTemplate fields have correct defaults."""
    rt = ReportTemplate.objects.create(
        tenant_id=tenant_id,
        name="Default Report",
        created_by="user-001",
    )
    assert rt.category == "general"
    assert rt.format == "pdf"
    assert rt.is_favorite is False
    assert rt.config == {}
    assert rt.description == ""


@pytest.mark.django_db
def test_report_template_unique_name_per_tenant(tenant_id: str) -> None:
    """Duplicate report name within same tenant raises IntegrityError."""
    ReportTemplate.objects.create(
        tenant_id=tenant_id,
        name="Unique Report",
        created_by="user-001",
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ReportTemplate.objects.create(
                tenant_id=tenant_id,
                name="Unique Report",
                created_by="user-002",
            )


@pytest.mark.django_db
def test_report_template_all_formats(tenant_id: str) -> None:
    """All format choices can be stored."""
    formats = ["pdf", "csv", "excel", "json"]
    for fmt in formats:
        rt = ReportTemplate.objects.create(
            tenant_id=tenant_id,
            name=f"Report {fmt}",
            format=fmt,
            created_by="user-001",
        )
        assert rt.format == fmt


@pytest.mark.django_db
def test_report_template_config_json(report_template: ReportTemplate) -> None:
    """config JSON field stores report configuration."""
    assert report_template.config["metrics"] == ["engagement_rate", "reach", "impressions"]
    assert report_template.config["visualizations"] == ["line_chart", "table"]


# ---------------------------------------------------------------------------
# ReportSchedule tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_report_schedule_creation(
    tenant_id: str,
    report_template: ReportTemplate,
) -> None:
    """ReportSchedule can be created linked to a ReportTemplate."""
    schedule = ReportSchedule.objects.create(
        tenant_id=tenant_id,
        template=report_template,
        name="Weekly Schedule",
        frequency="weekly",
        next_run_at=timezone.now() + timedelta(days=7),
        delivery={"email": ["team@example.com"]},
        timezone="America/New_York",
        is_active=True,
        created_by="user-001",
    )
    assert schedule.id is not None
    assert isinstance(schedule.id, uuid.UUID)
    assert schedule.name == "Weekly Schedule"
    assert schedule.frequency == "weekly"
    assert schedule.template == report_template


@pytest.mark.django_db
def test_report_schedule_str(report_template: ReportTemplate, tenant_id: str) -> None:
    """String representation includes name and frequency."""
    schedule = ReportSchedule.objects.create(
        tenant_id=tenant_id,
        template=report_template,
        name="Daily Schedule",
        frequency="daily",
        created_by="user-001",
    )
    assert str(schedule) == "Daily Schedule (daily)"


@pytest.mark.django_db
def test_report_schedule_defaults(
    tenant_id: str,
    report_template: ReportTemplate,
) -> None:
    """ReportSchedule fields have correct defaults."""
    schedule = ReportSchedule.objects.create(
        tenant_id=tenant_id,
        template=report_template,
        name="Default Schedule",
        created_by="user-001",
    )
    assert schedule.frequency == "weekly"
    assert schedule.cron_expression == ""
    assert schedule.next_run_at is None
    assert schedule.last_run_at is None
    assert schedule.last_run_status == "draft"
    assert schedule.last_run_result == {}
    assert schedule.delivery == {}
    assert schedule.timezone == "UTC"
    assert schedule.is_active is True


@pytest.mark.django_db
def test_report_schedule_frequency_choices(
    tenant_id: str,
    report_template: ReportTemplate,
) -> None:
    """All frequency choices can be stored."""
    frequencies = ["once", "hourly", "daily", "weekly", "monthly"]
    for freq in frequencies:
        schedule = ReportSchedule.objects.create(
            tenant_id=tenant_id,
            template=report_template,
            name=f"Schedule {freq}",
            frequency=freq,
            created_by="user-001",
        )
        assert schedule.frequency == freq


@pytest.mark.django_db
def test_report_schedule_related_to_template(
    report_template: ReportTemplate,
    tenant_id: str,
) -> None:
    """ReportSchedule is linked to ReportTemplate via foreign key."""
    schedule = ReportSchedule.objects.create(
        tenant_id=tenant_id,
        template=report_template,
        name="Linked Schedule",
        created_by="user-001",
    )
    assert schedule.template == report_template
    assert report_template.schedules.count() == 1


@pytest.mark.django_db
def test_report_schedule_last_run_result(
    report_template: ReportTemplate,
    tenant_id: str,
) -> None:
    """last_run_result stores JSON execution results."""
    schedule = ReportSchedule.objects.create(
        tenant_id=tenant_id,
        template=report_template,
        name="Run Result Schedule",
        last_run_status="completed",
        last_run_result={
            "status": "success",
            "file_url": "https://cdn.example.com/report.pdf",
            "records": 1500,
        },
        created_by="user-001",
    )
    assert schedule.last_run_result["status"] == "success"
    assert schedule.last_run_result["records"] == 1500


@pytest.mark.django_db
def test_report_schedule_delivery_config(
    report_template: ReportTemplate,
    tenant_id: str,
) -> None:
    """delivery JSON stores multi-channel delivery config."""
    schedule = ReportSchedule.objects.create(
        tenant_id=tenant_id,
        template=report_template,
        name="Multi Delivery",
        delivery={
            "email": ["team@example.com", "boss@example.com"],
            "slack": "#analytics",
            "webhook": "https://hooks.example.com/report",
        },
        created_by="user-001",
    )
    assert schedule.delivery["slack"] == "#analytics"
    assert len(schedule.delivery["email"]) == 2
