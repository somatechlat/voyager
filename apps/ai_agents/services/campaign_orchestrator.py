"""Campaign orchestrator — coordinates AI agents for marketing workflows.

Integrates Voyant (data intelligence), LLM Router (content generation),
and Vortex (workflow DAG execution) to implement UC-001: AI-assisted
campaign creation. Three specialized agents cooperate:

1. Research Agent — gathers intelligence via Voyant
2. Creative Agent — generates content via LLM Router
3. Optimization Agent — monitors performance via analytics

Usage::

    from apps.ai_agents.services.campaign_orchestrator import (
        CampaignOrchestrator,
    )

    orchestrator = CampaignOrchestrator()
    results = await orchestrator.run_campaign_workflow(
        client_id="acme_corp",
        campaign_id="camp_2025q1",
        tenant_id="tenant_42",
        token=jwt_token,
    )
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from apps.ai_agents.services.campaign_prompts import (
    build_brief_prompt,
    build_content_prompt,
    build_creative_context,
    build_email_prompt,
    build_social_prompt,
)
from apps.ai_agents.services.llm_router import LLMRouter
from vortex_bridge.client import vortex_client
from voyant_bridge.client import voyant_client

logger = logging.getLogger(__name__)


class CampaignOrchestrator:
    """Orchestrates AI agents through the complete marketing campaign workflow.

    Flow:
        1. Research Agent gathers data via Voyant (scraping, NLP, analysis)
        2. Creative Agent generates content via LLM Router (text, images)
        3. Workflow Agent submits to Vortex for DAG execution
    """

    def __init__(self) -> None:
        self.llm = LLMRouter()

    async def run_campaign_workflow(
        self,
        client_id: str,
        campaign_id: str,
        tenant_id: str,
        token: str,
        brand_kit: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Execute the complete AI-assisted campaign workflow (UC-001).

        Coordinates Research, Creative, and Vortex workflow agents.

        Args:
            client_id: Client identifier for data scoping.
            campaign_id: Campaign identifier.
            tenant_id: Tenant identifier for multi-tenancy.
            token: Bearer JWT token from Keycloak.
            brand_kit: Optional brand guidelines dict.

        Returns:
            Dict with research, creative, workflow results and aggregate cost.
        """
        results: dict[str, Any] = {
            "client_id": client_id,
            "campaign_id": campaign_id,
            "tenant_id": tenant_id,
        }
        total_cost = 0.0
        total_tokens = 0

        # Step 1: Research Agent
        logger.info(
            "UC-001: Starting Research Agent for client=%s", client_id
        )
        try:
            research = await self._run_research_agent(
                client_id, tenant_id, token
            )
            results["research"] = research
            meta = research.get("_meta", {})
            total_cost += meta.get("cost_usd", 0.0)
        except Exception as exc:
            logger.error("Research Agent failed: %s", exc)
            results["research"] = {"status": "error", "error": str(exc)}

        # Step 2: Creative Agent
        logger.info(
            "UC-001: Starting Creative Agent for campaign=%s", campaign_id
        )
        try:
            research_data = results.get("research", {})
            creative = await self._run_creative_agent(
                campaign_id=campaign_id,
                research=research_data,
                tenant_id=tenant_id,
                token=token,
                brand_kit=brand_kit,
            )
            results["creative"] = creative
            for key in ("brief", "content", "social_posts", "email_copy"):
                item = creative.get(key, {})
                if isinstance(item, dict):
                    total_cost += item.get("cost_usd", 0.0)
                    total_tokens += item.get("tokens_used", 0)
        except Exception as exc:
            logger.error("Creative Agent failed: %s", exc)
            results["creative"] = {"status": "error", "error": str(exc)}

        # Step 3: Submit to Vortex
        logger.info(
            "UC-001: Submitting to Vortex for campaign=%s", campaign_id
        )
        try:
            workflow = await self._submit_to_vortex(
                campaign_id=campaign_id,
                results=results,
                tenant_id=tenant_id,
                token=token,
            )
            results["workflow"] = workflow
        except Exception as exc:
            logger.error("Vortex workflow submission failed: %s", exc)
            results["workflow"] = {"status": "error", "error": str(exc)}

        results["aggregate"] = {
            "total_cost_usd": round(total_cost, 6),
            "total_tokens_used": total_tokens,
            "workflow_graph_id": results.get("workflow", {}).get("graph_id"),
            "workflow_run_id": results.get("workflow", {}).get("run_id"),
        }

        logger.info(
            "UC-001: Campaign workflow complete client=%s campaign=%s "
            "cost=$%s",
            client_id,
            campaign_id,
            total_cost,
        )
        return results

    async def generate_content(
        self,
        prompt: str,
        content_type: str,
        tenant_id: str,
        token: str,
        context: Optional[dict[str, Any]] = None,
        brand_kit: Optional[dict[str, Any]] = None,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        """Generate AI content with brand enforcement.

        Args:
            prompt: Generation prompt.
            content_type: One of ``text``, "image", "multimodal".
            tenant_id: Tenant identifier.
            token: Bearer JWT token.
            context: Optional context dict.
            brand_kit: Optional brand guidelines.
            max_tokens: Maximum output tokens (text only).

        Returns:
            Generation result dict.
        """
        ctx = context or {}

        if content_type == "text":
            return await self.llm.generate_text(
                prompt=prompt,
                context=ctx,
                brand_kit=brand_kit,
                max_tokens=max_tokens,
            )
        elif content_type == "image":
            return await self.llm.generate_image(
                prompt=prompt,
                brand_kit=brand_kit,
            )
        elif content_type == "multimodal":
            image_urls = ctx.get("image_urls", [])
            return await self.llm.generate_multimodal(
                prompt=prompt,
                image_urls=image_urls,
                max_tokens=max_tokens,
            )
        else:
            raise ValueError(f"Unsupported content_type: {content_type}")

    # ─────────────────────────────────────────────────────────────
    # Research Agent
    # ─────────────────────────────────────────────────────────────

    async def _run_research_agent(
        self,
        client_id: str,
        tenant_id: str,
        token: str,
    ) -> dict[str, Any]:
        """Research Agent: gathers intelligence via Voyant.

        Gathers competitor intelligence, market trends, audience insights,
        keyword research, and brand sentiment.
        """
        research_cost = 0.0

        try:
            competitor_data = await voyant_client.analyze_competitors(
                client_id=client_id,
                competitors=[],
                token=token,
                depth="standard",
            )
        except Exception as exc:
            logger.warning("Competitor analysis failed: %s", exc)
            competitor_data = {"status": "error", "error": str(exc)}

        try:
            trend_data = await voyant_client.analyze_market_trends(
                client_id=client_id,
                industry="general",
                token=token,
                timeframe_months=6,
            )
        except Exception as exc:
            logger.warning("Market trend analysis failed: %s", exc)
            trend_data = {"status": "error", "error": str(exc)}

        try:
            audience_data = await voyant_client.get_audience_insights(
                client_id=client_id,
                token=token,
            )
        except Exception as exc:
            logger.warning("Audience insights failed: %s", exc)
            audience_data = {"status": "error", "error": str(exc)}

        try:
            keywords = await voyant_client.search_keywords(
                query=f"marketing strategy {client_id}",
                token=token,
                limit=50,
            )
        except Exception as exc:
            logger.warning("Keyword search failed: %s", exc)
            keywords = {"status": "error", "error": str(exc)}

        try:
            sentiment = await voyant_client.analyze_brand_sentiment(
                client_id=client_id,
                token=token,
                days=30,
            )
        except Exception as exc:
            logger.warning("Brand sentiment analysis failed: %s", exc)
            sentiment = {"status": "error", "error": str(exc)}

        return {
            "competitors": competitor_data,
            "trends": trend_data,
            "audience": audience_data,
            "keywords": keywords,
            "sentiment": sentiment,
            "_meta": {"cost_usd": research_cost},
        }

    # ─────────────────────────────────────────────────────────────
    # Creative Agent
    # ─────────────────────────────────────────────────────────────

    async def _run_creative_agent(
        self,
        campaign_id: str,
        research: dict[str, Any],
        tenant_id: str,
        token: str,
        brand_kit: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Creative Agent: generates content via LLM Router.

        Generates campaign brief, marketing copy, social posts,
        and email copy based on research data.
        """
        context = build_creative_context(research)
        bk = brand_kit or {"voice": "professional", "tone": "friendly"}

        brief_prompt = build_brief_prompt(campaign_id, research)
        brief = await self.llm.generate_text(
            prompt=brief_prompt,
            context=context,
            brand_kit=bk,
            max_tokens=3000,
            preferred_model="anthropic",
        )

        content_prompt = build_content_prompt(campaign_id, brief, research)
        content = await self.llm.generate_text(
            prompt=content_prompt,
            context=context,
            brand_kit=bk,
            max_tokens=4000,
            preferred_model="openai",
        )

        social_prompt = build_social_prompt(campaign_id, brief, research)
        social_posts = await self.llm.generate_text(
            prompt=social_prompt,
            context=context,
            brand_kit=bk,
            max_tokens=2000,
            preferred_model="openai",
        )

        email_prompt = build_email_prompt(campaign_id, brief, research)
        email_copy = await self.llm.generate_text(
            prompt=email_prompt,
            context=context,
            brand_kit=bk,
            max_tokens=2500,
            preferred_model="anthropic",
        )

        return {
            "brief": brief,
            "content": content,
            "social_posts": social_posts,
            "email_copy": email_copy,
        }

    # ─────────────────────────────────────────────────────────────
    # Vortex Workflow Agent
    # ─────────────────────────────────────────────────────────────

    async def _submit_to_vortex(
        self,
        campaign_id: str,
        results: dict[str, Any],
        tenant_id: str,
        token: str,
    ) -> dict[str, Any]:
        """Submit campaign workflow to Vortex for DAG execution.

        Creates a workflow DAG: ingest → review → publish → monitor → optimize.
        """
        graph_dsl = {
            "nodes": [
                {
                    "id": "ingest",
                    "type": "action",
                    "config": {
                        "action": "ingest_campaign_data",
                        "campaign_id": campaign_id,
                        "tenant_id": tenant_id,
                    },
                },
                {
                    "id": "review",
                    "type": "human_approval",
                    "config": {
                        "timeout": 86400,
                        "approvers": ["campaign_manager"],
                    },
                },
                {
                    "id": "publish",
                    "type": "action",
                    "config": {
                        "action": "publish_content",
                        "campaign_id": campaign_id,
                        "channels": ["social", "email", "web"],
                    },
                },
                {
                    "id": "monitor",
                    "type": "action",
                    "config": {
                        "action": "start_monitoring",
                        "campaign_id": campaign_id,
                        "metrics": ["engagement", "conversion", "reach"],
                    },
                },
                {
                    "id": "optimize",
                    "type": "action",
                    "config": {
                        "action": "auto_optimize",
                        "campaign_id": campaign_id,
                        "rules": ["ab_test", "budget_reallocation"],
                    },
                },
            ],
            "edges": [
                {"from": "ingest", "to": "review"},
                {"from": "review", "to": "publish", "condition": "approved"},
                {"from": "review", "to": "ingest", "condition": "rejected"},
                {"from": "publish", "to": "monitor"},
                {
                    "from": "monitor",
                    "to": "optimize",
                    "condition": "threshold_met",
                },
            ],
        }

        graph_id = await vortex_client.submit_graph(graph_dsl, token)
        run_id = await vortex_client.execute_graph(graph_id, token)

        return {
            "graph_id": graph_id,
            "run_id": run_id,
            "status": "submitted",
            "nodes": [n["id"] for n in graph_dsl["nodes"]],
        }
