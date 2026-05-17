"""HTTP client for the Vortex workflow engine (Rust, port 11188).

Provides an async interface to Vortex's REST API endpoints for graph
submission, execution, run monitoring, MCP tool discovery and invocation.

All methods accept a JWT bearer ``token`` extracted from the incoming
Django/Keycloak request and forward it to Vortex for tenant-scoped
authorization.

Usage::

    from vortex_bridge.client import vortex_client

    graph_id = await vortex_client.submit_graph(graph_dsl, token)
    run_id   = await vortex_client.execute_graph(graph_id, token)
    status   = await vortex_client.get_run_status(run_id, token)

Always close the client on shutdown::

    await vortex_client.close()
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class VortexClient:
    """Async HTTP client for Vortex workflow engine.

    Endpoints mirror the Axum router defined in ``vortex-core/src/api.rs``.

    :param base_url: Vortex HTTP base URL (default: ``http://vortex-core:11188``).
    :param timeout: Request timeout in seconds (default: ``30.0``).
    """

    BASE_URL: str = "http://vortex-core:11188"
    TIMEOUT: float = 30.0

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self.base_url: str = base_url or self.BASE_URL
        self.timeout: float = timeout or self.TIMEOUT
        self._client: httpx.AsyncClient = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
        )

    # ─────────────────────────────────────────────────────────────
    # Graph lifecycle
    # ─────────────────────────────────────────────────────────────

    async def submit_graph(
        self,
        graph_dsl: Dict[str, Any],
        token: str,
        priority: Optional[str] = None,
    ) -> str:
        """Submit a workflow graph to Vortex.

        Maps to ``POST /api/graph`` in Vortex's Axum router.

        :param graph_dsl: GraphDSL dictionary defining nodes, edges and
            configuration for the workflow.
        :param token: Bearer JWT token from Keycloak.
        :param priority: Optional execution priority (``"high"`` | ``"low"``).
        :returns: The UUID ``graph_id`` assigned by Vortex.
        :raises httpx.HTTPStatusError: On 4xx/5xx from Vortex.
        """
        payload: Dict[str, Any] = {"graph": graph_dsl}
        if priority is not None:
            payload["priority"] = priority

        response = await self._client.post(
            f"{self.base_url}/api/graph",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        data: Dict[str, Any] = response.json()
        graph_id: str = data["graph_id"]
        logger.info("Graph submitted: %s (version=%s)", graph_id, data.get("version"))
        return graph_id

    async def get_graph(
        self,
        graph_id: str,
        token: str,
    ) -> Dict[str, Any]:
        """Retrieve a previously submitted graph.

        Maps to ``GET /api/graph/:id``.

        :param graph_id: UUID of the graph.
        :param token: Bearer JWT token.
        :returns: The graph DSL JSON as a dictionary.
        :raises httpx.HTTPStatusError: On 404 or other errors.
        """
        response = await self._client.get(
            f"{self.base_url}/api/graph/{graph_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()

    async def execute_graph(
        self,
        graph_id: str,
        token: str,
        full: bool = True,
        output_nodes: Optional[List[str]] = None,
    ) -> str:
        """Execute a submitted graph.

        Maps to ``POST /api/graph/:id/execute``.

        :param graph_id: UUID of the graph to execute.
        :param token: Bearer JWT token.
        :param full: Whether to execute all nodes or only partial.
        :param output_nodes: Optional list of node IDs to capture as output.
        :returns: The UUID ``run_id`` for tracking execution.
        :raises httpx.HTTPStatusError: On 4xx/5xx from Vortex.
        """
        payload: Dict[str, Any] = {"full": full}
        if output_nodes is not None:
            payload["output_nodes"] = output_nodes

        response = await self._client.post(
            f"{self.base_url}/api/graph/{graph_id}/execute",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        data: Dict[str, Any] = response.json()
        run_id: str = data["run_id"]
        logger.info(
            "Graph execution started: graph_id=%s run_id=%s eta_ms=%s",
            graph_id,
            run_id,
            data.get("estimated_time_ms"),
        )
        return run_id

    # ─────────────────────────────────────────────────────────────
    # Run monitoring
    # ─────────────────────────────────────────────────────────────

    async def get_run_status(
        self,
        run_id: str,
        token: str,
    ) -> Dict[str, Any]:
        """Check the status of a running or completed graph execution.

        Maps to ``GET /api/run/:id/status``.

        :param run_id: UUID of the run.
        :param token: Bearer JWT token.
        :returns: Dictionary with ``run_id``, ``status``, ``progress``
            (0.0–1.0 float), and optional ``current_node``.
        """
        response = await self._client.get(
            f"{self.base_url}/api/run/{run_id}/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()

    async def cancel_run(self, run_id: str, token: str) -> bool:
        """Cancel an active graph execution.

        Maps to ``POST /api/run/:id/cancel``.

        :param run_id: UUID of the run to cancel.
        :param token: Bearer JWT token.
        :returns: ``True`` if cancellation was accepted (HTTP 200),
            ``False`` otherwise.
        """
        response = await self._client.post(
            f"{self.base_url}/api/run/{run_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 200:
            logger.info("Run cancelled: %s", run_id)
            return True
        logger.warning(
            "Failed to cancel run %s: status=%s", run_id, response.status_code
        )
        return False

    # ─────────────────────────────────────────────────────────────
    # MCP (Model Context Protocol) integration
    # ─────────────────────────────────────────────────────────────

    async def list_mcp_tools(self, token: str) -> List[Dict[str, Any]]:
        """List all available MCP tool node definitions.

        Maps to ``GET /api/nodes/mcp``.

        :param token: Bearer JWT token.
        :returns: List of node definition dictionaries with ``type_id``,
            ``name``, ``description``, ``inputs``, ``outputs``,
            ``parameters``.
        """
        response = await self._client.get(
            f"{self.base_url}/api/nodes/mcp",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()

    async def list_mcp_clients(self, token: str) -> List[str]:
        """List registered MCP client IDs.

        Maps to ``GET /api/mcp/clients``.

        :param token: Bearer JWT token.
        :returns: List of registered MCP client ID strings.
        """
        response = await self._client.get(
            f"{self.base_url}/api/mcp/clients",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()

    async def call_mcp_tool(
        self,
        type_id: str,
        arguments: Dict[str, Any],
        token: str,
    ) -> Dict[str, Any]:
        """Invoke an MCP tool by its VORTEX type_id.

        Maps to ``POST /api/mcp/tool/call``.

        :param type_id: VORTEX node type identifier (e.g.
            ``"vortex.file.read"``).
        :param arguments: Tool-specific arguments as a dictionary.
        :param token: Bearer JWT token.
        :returns: Dictionary with ``type_id`` and ``result``.
        """
        response = await self._client.post(
            f"{self.base_url}/api/mcp/tool/call",
            json={"type_id": type_id, "arguments": arguments},
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()

    async def register_mcp_client(
        self,
        client_id: str,
        command: str,
        args: List[str],
        token: str,
    ) -> bool:
        """Register a stdio MCP client with Vortex.

        Maps to ``POST /api/mcp/client/register``.

        :param client_id: Unique client identifier.
        :param command: Executable command path.
        :param args: Command-line arguments for the MCP server.
        :param token: Bearer JWT token.
        :returns: ``True`` if registration succeeded (HTTP 201).
        """
        response = await self._client.post(
            f"{self.base_url}/api/mcp/client/register",
            json={"id": client_id, "command": command, "args": args},
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 201:
            logger.info("MCP client registered: %s", client_id)
            return True
        logger.warning(
            "MCP client registration failed: %s status=%s",
            client_id,
            response.status_code,
        )
        return False

    # ─────────────────────────────────────────────────────────────
    # Health & observability
    # ─────────────────────────────────────────────────────────────

    async def health_check(self) -> Dict[str, Any]:
        """Check Vortex health (unauthenticated, suitable for K8s probes).

        Maps to ``GET /health``.

        :returns: Dictionary with ``status`` (``"healthy"`` |
            ``"degraded"``), ``version``, and ``checks`` sub-dict.
        """
        response = await self._client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    async def get_metrics(self) -> str:
        """Retrieve Prometheus metrics from Vortex.

        Maps to ``GET /metrics``.

        :returns: Raw Prometheus text exposition.
        """
        response = await self._client.get(f"{self.base_url}/metrics")
        response.raise_for_status()
        return response.text

    # ─────────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────────

    async def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        await self._client.aclose()
        logger.debug("VortexClient closed")

    async def __aenter__(self) -> "VortexClient":
        return self

    async def __aexit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> None:
        await self.close()


# ═══════════════════════════════════════════════════════════════
#                    Singleton instance
# ═══════════════════════════════════════════════════════════════

vortex_client: VortexClient = VortexClient()
