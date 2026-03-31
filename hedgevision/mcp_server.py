"""MCP-compatible tool server exposing HedgeVision quant tools."""

from __future__ import annotations

from typing import Any

from hedgevision.core.market_intel import (
    analyze_sentiment,
    compute_quant_metrics,
    fetch_market_data,
)


def run_mcp_server() -> None:
    """Run MCP server over stdio.

    Requires the `mcp` package at runtime:
      pip install mcp
    """
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "MCP server runtime requires `mcp`. Install it with: pip install mcp"
        ) from e

    server = FastMCP("hedgevision")

    @server.tool()
    def hv_fetch_market_data(ticker: str) -> dict[str, Any]:
        """Fetch basic market data for a ticker."""
        return fetch_market_data(ticker).model_dump()

    @server.tool()
    def hv_compute_quant_metrics(ticker: str, period: str = "1y") -> dict[str, Any]:
        """Compute quant metrics including 50-day SMA."""
        return compute_quant_metrics(ticker, period=period).model_dump()

    @server.tool()
    def hv_analyze_sentiment(url: str) -> dict[str, Any]:
        """Analyze sentiment for a URL."""
        return analyze_sentiment(url).model_dump()

    server.run()
