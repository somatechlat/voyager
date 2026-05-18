"""Campaign workflow schemas for AI agent orchestration."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from ninja import Schema


class BrandKitSchema(Schema):
    """Brand guidelines for content generation."""

    voice: str = "professional"
    tone: str = "friendly"
    tone_rules: str = ""
    forbidden_words: list[str] = []
    required_phrases: list[str] = []
    color_palette: list[str] = []
    logo_url: str = ""


class CampaignWorkflowRequest(Schema):
    """Request body to launch a campaign workflow (UC-001)."""

    tenant_id: str
    brand_kit: Optional[BrandKitSchema] = None


class LLMResultSchema(Schema):
    """Single LLM generation result."""

    text: str = ""
    model_used: str = ""
    tokens_used: int = 0
    cost_usd: float = 0.0
    brand_compliance_score: Optional[float] = None


class ImageResultSchema(Schema):
    """Image generation result."""

    image_url: str = ""
    model_used: str = ""
    revised_prompt: str = ""
    cost_usd: float = 0.0


class ResearchDataSchema(Schema):
    """Research agent output data."""

    competitors: dict[str, Any] = {}
    trends: dict[str, Any] = {}
    audience: dict[str, Any] = {}
    keywords: dict[str, Any] = {}
    sentiment: dict[str, Any] = {}


class CreativeOutputSchema(Schema):
    """Creative agent output with all content assets."""

    brief: LLMResultSchema = LLMResultSchema()
    content: LLMResultSchema = LLMResultSchema()
    social_posts: LLMResultSchema = LLMResultSchema()
    email_copy: LLMResultSchema = LLMResultSchema()


class WorkflowStatusSchema(Schema):
    """Vortex workflow submission result."""

    graph_id: str = ""
    run_id: str = ""
    status: str = ""
    nodes: list[str] = []


class CampaignWorkflowResponse(Schema):
    """Full campaign workflow response (UC-001)."""

    client_id: str = ""
    campaign_id: str = ""
    tenant_id: str = ""
    research: ResearchDataSchema = ResearchDataSchema()
    creative: CreativeOutputSchema = CreativeOutputSchema()
    workflow: WorkflowStatusSchema = WorkflowStatusSchema()
    aggregate: dict[str, Any] = {}


class GenerateContentRequest(Schema):
    """Request body for single content generation."""

    prompt: str
    content_type: str = "text"  # text | image | multimodal
    context: dict[str, Any] = {}
    brand_kit: Optional[BrandKitSchema] = None
    max_tokens: int = 2000
    tenant_id: str = ""


class GenerateContentResponse(Schema):
    """Response for single content generation."""

    text: str = ""
    image_url: str = ""
    model_used: str = ""
    tokens_used: int = 0
    cost_usd: float = 0.0
    brand_compliance_score: Optional[float] = None


class WorkflowStatusResponse(Schema):
    """Check Vortex workflow execution status."""

    run_id: str
    graph_id: str = ""
    status: str = ""
    progress: float = 0.0
    current_node: str = ""
    updated_at: datetime | None = None


class CampaignWorkflowListItem(Schema):
    """Summary item for workflow history."""

    client_id: str = ""
    campaign_id: str = ""
    tenant_id: str = ""
    workflow: WorkflowStatusSchema = WorkflowStatusSchema()
    aggregate: dict[str, Any] = {}
    created_at: datetime | None = None
