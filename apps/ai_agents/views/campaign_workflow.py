"""Campaign workflow views — UC-001 AI-assisted campaign orchestration.

Provides endpoints for executing the complete AI-assisted campaign workflow
coordinating Research Agent (Voyant data), Creative Agent (LLM Router),
and Vortex workflow execution.
"""

from __future__ import annotations

import logging
from typing import Any

from django.http import HttpRequest

from apps.ai_agents.serializers.campaign_workflow import (
    BrandKitSchema,
    CampaignWorkflowRequest,
    CampaignWorkflowResponse,
    GenerateContentRequest,
    GenerateContentResponse,
    WorkflowStatusResponse,
)
from apps.ai_agents.services.campaign_orchestrator import CampaignOrchestrator
from vortex_bridge.client import vortex_client

logger = logging.getLogger(__name__)

# Module-level singleton — reused across requests
_orchestrator: CampaignOrchestrator | None = None


def _get_orchestrator() -> CampaignOrchestrator:
    """Lazy-initialize the campaign orchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = CampaignOrchestrator()
    return _orchestrator


async def run_campaign_workflow(
    request: HttpRequest,
    client_id: str,
    campaign_id: str,
    payload: CampaignWorkflowRequest,
) -> CampaignWorkflowResponse:
    """Execute the complete AI-assisted campaign workflow (UC-001).

    Coordinates Research Agent (Voyant data), Creative Agent (LLM),
    and Vortex workflow execution. Requires client_id and campaign_id
    as path parameters; tenant_id and optional brand_kit in body.

    Returns:
        CampaignWorkflowResponse with research, creative, workflow results.
    """
    token = request.headers.get("Authorization", "").replace("Bearer ", "")

    orchestrator = _get_orchestrator()
    brand_kit = payload.brand_kit.dict() if payload.brand_kit else None

    results = await orchestrator.run_campaign_workflow(
        client_id=client_id,
        campaign_id=campaign_id,
        tenant_id=payload.tenant_id,
        token=token,
        brand_kit=brand_kit,
    )

    # Build response from raw results
    research_data = results.get("research", {})
    creative_data = results.get("creative", {})
    workflow_data = results.get("workflow", {})
    aggregate = results.get("aggregate", {})

    return CampaignWorkflowResponse(
        client_id=client_id,
        campaign_id=campaign_id,
        tenant_id=payload.tenant_id,
        research=_serialize_research(research_data),
        creative=_serialize_creative(creative_data),
        workflow=_serialize_workflow(workflow_data),
        aggregate=aggregate,
    )


async def generate_content(
    request: HttpRequest,
    payload: GenerateContentRequest,
) -> GenerateContentResponse:
    """Generate AI content with brand enforcement.

    Single-shot content generation via the LLM Router.
    Supports text, image, and multimodal content types.
    """
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    tenant_id = payload.tenant_id or request.headers.get("X-Tenant-ID", "")

    orchestrator = _get_orchestrator()
    brand_kit = payload.brand_kit.dict() if payload.brand_kit else None

    result = await orchestrator.generate_content(
        prompt=payload.prompt,
        content_type=payload.content_type,
        tenant_id=tenant_id,
        token=token,
        context=payload.context,
        brand_kit=brand_kit,
        max_tokens=payload.max_tokens,
    )

    return GenerateContentResponse(
        text=result.get("text", ""),
        image_url=result.get("image_url", ""),
        model_used=result.get("model_used", ""),
        tokens_used=result.get("tokens_used", 0),
        cost_usd=result.get("cost_usd", 0.0),
        brand_compliance_score=result.get("brand_compliance_score"),
    )


async def get_workflow_status(
    request: HttpRequest,
    run_id: str,
) -> WorkflowStatusResponse:
    """Check the status of a Vortex workflow execution.

    Queries Vortex for the current run state and progress.
    """
    token = request.headers.get("Authorization", "").replace("Bearer ", "")

    try:
        status = await vortex_client.get_run_status(run_id, token)
        return WorkflowStatusResponse(
            run_id=run_id,
            graph_id=status.get("graph_id", ""),
            status=status.get("status", "unknown"),
            progress=status.get("progress", 0.0),
            current_node=status.get("current_node", ""),
        )
    except Exception as exc:
        logger.warning("Failed to get workflow status for %s: %s", run_id, exc)
        return WorkflowStatusResponse(
            run_id=run_id,
            status="error",
            current_node=str(exc),
        )


async def cancel_workflow(
    request: HttpRequest,
    run_id: str,
) -> dict[str, Any]:
    """Cancel an active Vortex workflow execution."""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")

    cancelled = await vortex_client.cancel_run(run_id, token)
    return {"cancelled": cancelled, "run_id": run_id}


# ─────────────────────────────────────────────────────────────
# Serialization helpers
# ─────────────────────────────────────────────────────────────

def _serialize_research(data: dict[str, Any]) -> Any:
    """Serialize research data into ResearchDataSchema-compatible dict."""
    from apps.ai_agents.serializers.campaign_workflow import ResearchDataSchema

    return ResearchDataSchema(
        competitors=_safe_dict(data.get("competitors")),
        trends=_safe_dict(data.get("trends")),
        audience=_safe_dict(data.get("audience")),
        keywords=_safe_dict(data.get("keywords")),
        sentiment=_safe_dict(data.get("sentiment")),
    )


def _serialize_creative(data: dict[str, Any]) -> Any:
    """Serialize creative data into CreativeOutputSchema-compatible dict."""
    from apps.ai_agents.serializers.campaign_workflow import (
        CreativeOutputSchema,
        LLMResultSchema,
    )

    def _llm(item: Any) -> Any:
        if isinstance(item, dict):
            return LLMResultSchema(
                text=item.get("text", ""),
                model_used=item.get("model_used", ""),
                tokens_used=item.get("tokens_used", 0),
                cost_usd=item.get("cost_usd", 0.0),
                brand_compliance_score=item.get("brand_compliance_score"),
            )
        return LLMResultSchema()

    return CreativeOutputSchema(
        brief=_llm(data.get("brief")),
        content=_llm(data.get("content")),
        social_posts=_llm(data.get("social_posts")),
        email_copy=_llm(data.get("email_copy")),
    )


def _serialize_workflow(data: dict[str, Any]) -> Any:
    """Serialize workflow data into WorkflowStatusSchema-compatible dict."""
    from apps.ai_agents.serializers.campaign_workflow import WorkflowStatusSchema

    if isinstance(data, dict):
        return WorkflowStatusSchema(
            graph_id=data.get("graph_id", ""),
            run_id=data.get("run_id", ""),
            status=data.get("status", ""),
            nodes=data.get("nodes", []),
        )
    return WorkflowStatusSchema()


def _safe_dict(value: Any) -> dict[str, Any]:
    """Safely convert value to dict."""
    if isinstance(value, dict):
        return value
    return {}
