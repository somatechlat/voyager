"""Ninja schemas for the Clients CRM module.

Defines request/response schemas for Client, ClientContact, Project,
ProjectMilestone, CommunicationLog, ClientPortal, and ClientProfitability.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from ninja import Schema

# ---------------------------------------------------------------------------
# Client schemas
# ---------------------------------------------------------------------------


class ClientCreateSchema(Schema):
    """Schema for creating a new client."""

    name: str
    slug: str
    industry: str = ""
    website: str = ""
    logo_url: str = ""
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    address: str = ""
    billing_address: str = ""
    tax_id: str = ""
    status: str = "active"
    tier: str = "basic"
    settings: dict[str, Any] = {}
    metadata: dict[str, Any] = {}


class ClientUpdateSchema(Schema):
    """Schema for updating an existing client."""

    name: str | None = None
    slug: str | None = None
    industry: str | None = None
    website: str | None = None
    logo_url: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    address: str | None = None
    billing_address: str | None = None
    tax_id: str | None = None
    status: str | None = None
    tier: str | None = None
    settings: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class ClientListSchema(Schema):
    """Schema for listing clients (lightweight)."""

    id: int
    name: str
    slug: str
    industry: str
    status: str
    tier: str
    contact_name: str
    contact_email: str
    created_at: datetime


class ClientDetailSchema(Schema):
    """Schema for retrieving a single client with full details."""

    id: int
    tenant_id: str
    name: str
    slug: str
    industry: str
    website: str
    logo_url: str
    contact_name: str
    contact_email: str
    contact_phone: str
    address: str
    billing_address: str
    tax_id: str
    status: str
    tier: str
    settings: dict[str, Any]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# ClientContact schemas
# ---------------------------------------------------------------------------


class ClientContactCreateSchema(Schema):
    """Schema for creating a client contact."""

    name: str
    email: str
    phone: str = ""
    role: str = ""
    is_primary: bool = False


class ClientContactUpdateSchema(Schema):
    """Schema for updating a client contact."""

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    role: str | None = None
    is_primary: bool | None = None


class ClientContactSchema(Schema):
    """Schema for a client contact response."""

    id: int
    client_id: int
    name: str
    email: str
    phone: str
    role: str
    is_primary: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Project schemas
# ---------------------------------------------------------------------------


class ProjectCreateSchema(Schema):
    """Schema for creating a new project."""

    name: str
    description: str = ""
    status: str = "planning"
    start_date: date | None = None
    end_date: date | None = None
    budget_amount: Decimal | None = None
    budget_type: str = "fixed"
    manager_id: str = ""
    team_ids: list[str] = []
    settings: dict[str, Any] = {}


class ProjectUpdateSchema(Schema):
    """Schema for updating an existing project."""

    name: str | None = None
    description: str | None = None
    status: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    budget_amount: Decimal | None = None
    budget_type: str | None = None
    manager_id: str | None = None
    team_ids: list[str] | None = None
    settings: dict[str, Any] | None = None


class ProjectListSchema(Schema):
    """Schema for listing projects (lightweight)."""

    id: int
    name: str
    status: str
    budget_type: str
    start_date: date | None
    end_date: date | None
    manager_id: str
    created_at: datetime


class ProjectDetailSchema(Schema):
    """Schema for retrieving a single project with full details."""

    id: int
    tenant_id: str
    client_id: int
    name: str
    description: str
    status: str
    start_date: date | None
    end_date: date | None
    budget_amount: Decimal | None
    budget_type: str
    manager_id: str
    team_ids: list[str]
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# ProjectMilestone schemas
# ---------------------------------------------------------------------------


class MilestoneCreateSchema(Schema):
    """Schema for creating a project milestone."""

    name: str
    description: str = ""
    due_date: date | None = None
    status: str = "pending"
    deliverables: list[dict[str, Any]] = []


class MilestoneUpdateSchema(Schema):
    """Schema for updating a project milestone."""

    name: str | None = None
    description: str | None = None
    due_date: date | None = None
    status: str | None = None
    deliverables: list[dict[str, Any]] | None = None


class MilestoneSchema(Schema):
    """Schema for a project milestone response."""

    id: int
    project_id: int
    name: str
    description: str
    due_date: date | None
    status: str
    deliverables: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# CommunicationLog schemas
# ---------------------------------------------------------------------------


class CommunicationCreateSchema(Schema):
    """Schema for creating a communication log entry."""

    project_id: int | None = None
    comm_type: str
    direction: str = "outbound"
    subject: str = ""
    content: str = ""
    participant_ids: list[str] = []
    duration_minutes: int | None = None
    metadata: dict[str, Any] = {}


class CommunicationUpdateSchema(Schema):
    """Schema for updating a communication log entry."""

    project_id: int | None = None
    comm_type: str | None = None
    direction: str | None = None
    subject: str | None = None
    content: str | None = None
    participant_ids: list[str] | None = None
    duration_minutes: int | None = None
    metadata: dict[str, Any] | None = None


class CommunicationSchema(Schema):
    """Schema for a communication log response."""

    id: int
    tenant_id: str
    client_id: int
    project_id: int | None
    comm_type: str
    direction: str
    subject: str
    content: str
    participant_ids: list[str]
    duration_minutes: int | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# ClientPortal schemas
# ---------------------------------------------------------------------------


class PortalCreateSchema(Schema):
    """Schema for creating a client portal."""

    slug: str
    branding: dict[str, Any] = {}
    custom_domain: str = ""
    is_active: bool = True


class PortalUpdateSchema(Schema):
    """Schema for updating a client portal."""

    slug: str | None = None
    branding: dict[str, Any] | None = None
    custom_domain: str | None = None
    is_active: bool | None = None


class PortalSchema(Schema):
    """Schema for a client portal response."""

    id: int
    client_id: int
    slug: str
    branding: dict[str, Any]
    custom_domain: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# ClientProfitability schemas
# ---------------------------------------------------------------------------


class ProfitabilityCreateSchema(Schema):
    """Schema for creating a profitability record."""

    period_start: date
    period_end: date
    revenue: Decimal = Decimal("0.00")
    costs: Decimal = Decimal("0.00")
    margin_percent: Decimal = Decimal("0.00")
    breakdown: dict[str, Any] = {}


class ProfitabilityUpdateSchema(Schema):
    """Schema for updating a profitability record."""

    period_start: date | None = None
    period_end: date | None = None
    revenue: Decimal | None = None
    costs: Decimal | None = None
    margin_percent: Decimal | None = None
    breakdown: dict[str, Any] | None = None


class ProfitabilitySchema(Schema):
    """Schema for a profitability response."""

    id: int
    tenant_id: str
    client_id: int
    period_start: date
    period_end: date
    revenue: Decimal
    costs: Decimal
    margin_percent: Decimal
    gross_profit: float
    breakdown: dict[str, Any]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Onboarding schema
# ---------------------------------------------------------------------------


class OnboardingCompleteSchema(Schema):
    """Schema for completing client onboarding."""

    onboarding_data: dict[str, Any] = {}


class OnboardingResponseSchema(Schema):
    """Schema for onboarding completion response."""

    client_id: int
    status: str
    completed_at: datetime
    message: str


# ---------------------------------------------------------------------------
# Pagination / list wrappers
# ---------------------------------------------------------------------------


class PaginatedClientsSchema(Schema):
    """Paginated list of clients."""

    count: int
    items: list[ClientListSchema]


class PaginatedProjectsSchema(Schema):
    """Paginated list of projects."""

    count: int
    items: list[ProjectListSchema]


class PaginatedMilestonesSchema(Schema):
    """Paginated list of milestones."""

    count: int
    items: list[MilestoneSchema]


class PaginatedCommunicationsSchema(Schema):
    """Paginated list of communication logs."""

    count: int
    items: list[CommunicationSchema]


class PaginatedProfitabilitySchema(Schema):
    """Paginated list of profitability records."""

    count: int
    items: list[ProfitabilitySchema]
