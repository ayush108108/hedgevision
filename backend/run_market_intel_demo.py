#!/usr/bin/env python3
"""
Quick demo runner for Market Intelligence pipeline.

Usage examples:
  python backend/run_market_intel_demo.py --ticker AAPL
  python backend/run_market_intel_demo.py --ticker MSFT --url https://example.com/news

If OPENAI_API_KEY is set and langgraph/langchain-openai installed, you can
later wire in agentic routing; for now we run the sequential pipeline which
does not require LLMs.
"""

from backend.agents.market_intel import _main_cli


if __name__ == "__main__":
    _main_cli()
