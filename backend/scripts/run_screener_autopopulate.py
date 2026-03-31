#!/usr/bin/env python3
"""Background worker entrypoint for screener precomputation."""

from __future__ import annotations

import asyncio

from backend.api.main import auto_populate_screener


def main() -> int:
    asyncio.run(auto_populate_screener())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

