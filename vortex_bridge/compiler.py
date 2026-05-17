"""Workflow-to-GraphDSL compiler.

Translates Voyager high-level workflow definitions into Vortex-compatible
GraphDSL structures. Each compilation method produces a dictionary that
conforms to the ``GraphRequest.graph`` schema expected by
:meth:`vortex_bridge.client.VortexClient.submit_graph`.

Usage::

    from vortex_bridge.compiler import workflow_compiler
    from vortex_bridge.client import vortex_client

    graph_dsl = workflow_compiler.compile_content_pipeline(brand_kit, templates)
    graph_id = await vortex_client.submit_graph(graph_dsl, token)
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)


class WorkflowCompiler:
    """Compiles Voyager workflow definitions to Vortex GraphDSL.

    The GraphDSL structure produced by each method contains:

    * ``nodes`` — list of node definitions with ``id``, ``type_id``,
      ``parameters``, and position metadata.
    * ``edges`` — list of connections mapping ``source`` → ``target``
      node IDs with optional ``source_port`` and ``target_port``.
    * ``metadata`` — workflow-level annotations (tenant, tags, etc.).
    """

    # ─────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────

    def compile_workflow(self, workflow: dict[str, Any]) -> dict[str, Any]:
        """Compile a generic Voyager workflow to Vortex GraphDSL.

        This is the entry-point for arbitrary workflows that already
        contain a ``nodes`` and ``edges`` structure. It validates
        and normalizes the definition rather than generating from
        scratch.

        :param workflow: Voyager workflow dictionary with at least
            ``nodes`` (list) and ``edges`` (list) keys.
        :returns: Normalized GraphDSL dictionary ready for submission.
        :raises ValueError: If the workflow is missing required keys.
        """
        if "nodes" not in workflow or "edges" not in workflow:
            raise ValueError("Workflow must contain 'nodes' and 'edges' keys")

        graph_dsl: dict[str, Any] = {
            "nodes": [self._normalize_node(n) for n in workflow["nodes"]],
            "edges": [self._normalize_edge(e) for e in workflow["edges"]],
            "metadata": workflow.get("metadata", {}),
        }

        logger.info(
            "Compiled generic workflow: %d nodes, %d edges",
            len(graph_dsl["nodes"]),
            len(graph_dsl["edges"]),
        )
        return graph_dsl

    def compile_content_pipeline(
        self,
        brand_kit: dict[str, Any],
        templates: list[dict[str, Any]],
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Compile a content-creation pipeline to GraphDSL.

        Generates a graph that:
        1. Loads the brand kit (tone, voice, guidelines).
        2. Selects a content template based on channel/type.
        3. Generates content via an LLM node.
        4. Applies brand-voice formatting.
        5. Outputs the final asset.

        :param brand_kit: Brand configuration with ``tone``, ``voice``,
            ``guidelines`` keys.
        :param templates: List of content templates, each with
            ``channel`` (``"blog"`` | ``"social"`` | ``"email"``) and
            ``structure`` keys.
        :param options: Optional pipeline overrides.
        :returns: GraphDSL dictionary.
        """
        brand_node = self._create_node(
            type_id="vortex.brand.load",
            parameters={"brand_kit": brand_kit},
        )
        template_node = self._create_node(
            type_id="vortex.template.select",
            parameters={"templates": templates},
        )
        generate_node = self._create_node(
            type_id="vortex.llm.generate",
            parameters={
                "model": "gpt-4o",
                "temperature": 0.7,
                "max_tokens": 2000,
            },
        )
        format_node = self._create_node(
            type_id="vortex.brand.apply_voice",
            parameters={},
        )
        output_node = self._create_node(
            type_id="vortex.asset.output",
            parameters={"format": options.get("output_format", "json") if options else "json"},
        )

        graph_dsl: dict[str, Any] = {
            "nodes": [brand_node, template_node, generate_node, format_node, output_node],
            "edges": [
                self._create_edge(brand_node["id"], generate_node["id"], "brand"),
                self._create_edge(template_node["id"], generate_node["id"], "template"),
                self._create_edge(generate_node["id"], format_node["id"], "draft"),
                self._create_edge(brand_node["id"], format_node["id"], "brand"),
                self._create_edge(format_node["id"], output_node["id"], "content"),
            ],
            "metadata": {
                "workflow_type": "content_pipeline",
                "template_count": len(templates),
                **(options or {}),
            },
        }

        logger.info("Compiled content pipeline: %d templates", len(templates))
        return graph_dsl

    def compile_campaign_workflow(
        self,
        campaign: dict[str, Any],
    ) -> dict[str, Any]:
        """Compile a campaign execution workflow to GraphDSL.

        Generates a graph that orchestrates multi-channel campaign
        execution: audience segmentation, asset preparation, channel
        dispatch, and budget tracking.

        :param campaign: Campaign definition with ``channels``,
            ``budget``, ``audience``, ``schedule`` keys.
        :returns: GraphDSL dictionary.
        """
        segment_node = self._create_node(
            type_id="vortex.audience.segment",
            parameters={"audience": campaign.get("audience", {})},
        )
        budget_node = self._create_node(
            type_id="vortex.budget.check",
            parameters={"budget": campaign.get("budget", {})},
        )

        channel_nodes: list[dict[str, Any]] = []
        channel_edges: list[dict[str, Any]] = []

        for channel in campaign.get("channels", []):
            ch_node = self._create_node(
                type_id=f"vortex.channel.{channel['type']}.dispatch",
                parameters=channel,
            )
            channel_nodes.append(ch_node)
            channel_edges.append(self._create_edge(segment_node["id"], ch_node["id"], "audience"))
            channel_edges.append(self._create_edge(budget_node["id"], ch_node["id"], "budget"))

        aggregate_node = self._create_node(
            type_id="vortex.metrics.aggregate",
            parameters={},
        )

        for ch_node in channel_nodes:
            channel_edges.append(self._create_edge(ch_node["id"], aggregate_node["id"], "metrics"))

        graph_dsl: dict[str, Any] = {
            "nodes": [segment_node, budget_node, *channel_nodes, aggregate_node],
            "edges": channel_edges,
            "metadata": {
                "workflow_type": "campaign",
                "campaign_name": campaign.get("name", "untitled"),
                "channel_count": len(channel_nodes),
            },
        }

        logger.info(
            "Compiled campaign workflow: %s with %d channels",
            campaign.get("name", "untitled"),
            len(channel_nodes),
        )
        return graph_dsl

    def compile_publishing_queue(
        self,
        posts: list[dict[str, Any]],
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Compile a publishing queue workflow to GraphDSL.

        Generates a parallel dispatch graph where each post is a
        branch that validates, optimises, and publishes to its
        target platform.

        :param posts: List of post definitions with ``platform``,
            ``content``, ``scheduled_at`` keys.
        :param options: Optional queue overrides (batch size, retry).
        :returns: GraphDSL dictionary.
        """
        post_nodes: list[dict[str, Any]] = []
        post_edges: list[dict[str, Any]] = []

        for post in posts:
            validate_node = self._create_node(
                type_id="vortex.content.validate",
                parameters={"rules": ["length", "hashtag_count", "link_count"]},
            )
            optimise_node = self._create_node(
                type_id="vortex.content.optimise",
                parameters={"platform": post["platform"]},
            )
            publish_node = self._create_node(
                type_id=f"vortex.platform.{post['platform']}.publish",
                parameters=post,
            )

            post_nodes.extend([validate_node, optimise_node, publish_node])
            post_edges.append(
                self._create_edge(validate_node["id"], optimise_node["id"], "content")
            )
            post_edges.append(self._create_edge(optimise_node["id"], publish_node["id"], "content"))

        graph_dsl: dict[str, Any] = {
            "nodes": post_nodes,
            "edges": post_edges,
            "metadata": {
                "workflow_type": "publishing_queue",
                "post_count": len(posts),
                "batch_size": (options or {}).get("batch_size", 10),
            },
        }

        logger.info("Compiled publishing queue: %d posts", len(posts))
        return graph_dsl

    # ─────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────

    def _create_node(
        self,
        type_id: str,
        parameters: dict[str, Any],
        position: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Create a normalized node dictionary.

        :param type_id: VORTEX node type identifier.
        :param parameters: Node-specific parameters.
        :param position: Optional visual ``{"x": int, "y": int}``.
        :returns: Normalized node dict with generated UUID ``id``.
        """
        return {
            "id": f"node_{uuid.uuid4().hex[:12]}",
            "type_id": type_id,
            "parameters": parameters,
            "position": position or {"x": 0, "y": 0},
        }

    def _create_edge(
        self,
        source: str,
        target: str,
        label: str | None = None,
        source_port: str | None = None,
        target_port: str | None = None,
    ) -> dict[str, Any]:
        """Create a normalized edge dictionary.

        :param source: Source node ``id``.
        :param target: Target node ``id``.
        :param label: Optional human-readable edge label.
        :param source_port: Optional source port name.
        :param target_port: Optional target port name.
        :returns: Normalized edge dict.
        """
        edge: dict[str, Any] = {
            "id": f"edge_{uuid.uuid4().hex[:8]}",
            "source": source,
            "target": target,
        }
        if label:
            edge["label"] = label
        if source_port:
            edge["source_port"] = source_port
        if target_port:
            edge["target_port"] = target_port
        return edge

    def _normalize_node(self, node: dict[str, Any]) -> dict[str, Any]:
        """Ensure a node dict has all required GraphDSL fields."""
        normalized = dict(node)
        if "id" not in normalized:
            normalized["id"] = f"node_{uuid.uuid4().hex[:12]}"
        if "position" not in normalized:
            normalized["position"] = {"x": 0, "y": 0}
        return normalized

    def _normalize_edge(self, edge: dict[str, Any]) -> dict[str, Any]:
        """Ensure an edge dict has all required GraphDSL fields."""
        normalized = dict(edge)
        if "id" not in normalized:
            normalized["id"] = f"edge_{uuid.uuid4().hex[:8]}"
        return normalized


# ═══════════════════════════════════════════════════════════════
#                    Singleton instance
# ═══════════════════════════════════════════════════════════════

workflow_compiler: WorkflowCompiler = WorkflowCompiler()
