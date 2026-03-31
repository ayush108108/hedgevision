"""Wrapper around scripts/pipelines/daily_eod_pipeline.py for CLI execution."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path


def _load_daily_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "pipelines" / "daily_eod_pipeline.py"
    if not script_path.exists():
        raise FileNotFoundError(f"Pipeline script not found: {script_path}")

    spec = importlib.util.spec_from_file_location("hedgevision_daily_eod_pipeline", script_path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Failed to load module spec for: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_daily_eod_sync() -> bool:
    """Run the daily EOD pipeline and return success status."""
    module = _load_daily_module()
    main_fn = getattr(module, "main", None)
    if main_fn is None:
        raise RuntimeError("daily_eod_pipeline.py does not expose async main()")
    return bool(asyncio.run(main_fn()))


if __name__ == "__main__":  # pragma: no cover
    ok = run_daily_eod_sync()
    raise SystemExit(0 if ok else 1)
