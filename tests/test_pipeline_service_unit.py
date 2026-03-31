from __future__ import annotations

from datetime import datetime
from typing import Dict

import pandas as pd
import pytest
import importlib
import sys
from pathlib import Path


def _get_pipeline_service_class():
    repo_root = Path(__file__).parent.parent
    backend_path = repo_root / "backend"
    # Ensure both root (for 'backend.*') and backend/ (for 'api.*') are importable
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    return importlib.import_module("api.services.pipeline_service").PipelineService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_pipeline_success_daily(monkeypatch):
    """
    Happy-path: run_pipeline orchestrates extract → transform → load for daily data.
    Risk: If orchestration breaks, we may fetch data but fail to persist (or vice versa),
    causing silent data gaps and downstream analytics errors.
    """
    PipelineService = _get_pipeline_service_class()
    svc = PipelineService()

    # Stub extract returns raw df (any shape); we'll transform into price schema
    raw_df = pd.DataFrame({"foo": [1, 2, 3]})
    async def _fake_extract(**kwargs):
        return raw_df
    monkeypatch.setattr(svc, "_extract_data", _fake_extract, raising=False)

    # Transform returns standardized DataFrame with expected columns for daily
    clean_df = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "Open": [10.0, 10.1, 10.2],
            "High": [10.5, 10.6, 10.7],
            "Low": [9.8, 9.9, 10.0],
            "Close": [10.3, 10.4, 10.5],
            "Volume": [100, 200, 300],
        }
    )
    monkeypatch.setattr(
        svc,
        "_transform_data",
        lambda df, symbol, validate=True: clean_df,
        raising=False,
    )

    # Count calls to data_writer.store_data without touching DB
    calls: Dict[str, int] = {"count": 0}

    def fake_store(symbol, df, source="yfinance"):
        calls["count"] += 1
        return len(df)

    monkeypatch.setattr(svc.data_writer, "store_data", fake_store, raising=False)

    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 10)
    result = await svc.run_pipeline("AAA", start, end, granularity="daily")

    assert result["status"] == "success"
    assert result["records_fetched"] == len(raw_df)
    assert result["records_stored"] == len(clean_df)
    assert result["granularity"] == "daily"
    assert calls["count"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_pipeline_validation_failure_partial(monkeypatch):
    PipelineService = _get_pipeline_service_class()
    svc = PipelineService()

    # Extract returns data
    async def _fake_extract_some(**k):
        return pd.DataFrame({"x": [1]})
    monkeypatch.setattr(svc, "_extract_data", _fake_extract_some, raising=False)
    # Transform returns empty (validation failed)
    monkeypatch.setattr(svc, "_transform_data", lambda *a, **k: pd.DataFrame(), raising=False)

    out = await svc.run_pipeline("AAA", datetime(2024, 1, 1), datetime(2024, 1, 2), granularity="daily")
    assert out["status"] == "partial"
    assert "validation" in (out.get("error") or "").lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_pipeline_no_data_failed(monkeypatch):
    PipelineService = _get_pipeline_service_class()
    svc = PipelineService()
    # Extract returns empty
    async def _fake_extract_empty(**k):
        return pd.DataFrame()
    monkeypatch.setattr(svc, "_extract_data", _fake_extract_empty, raising=False)

    out = await svc.run_pipeline("AAA", datetime(2024, 1, 1), datetime(2024, 1, 2), granularity="daily")
    assert out["status"] == "failed"
    assert "no data" in (out.get("error") or "").lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_pipeline_store_returns_zero_failed(monkeypatch):
    PipelineService = _get_pipeline_service_class()
    svc = PipelineService()

    # Extract some raw
    async def _fake_extract_two(**k):
        return pd.DataFrame({"x": [1, 2]})
    monkeypatch.setattr(svc, "_extract_data", _fake_extract_two, raising=False)
    # Transform to valid schema
    clean_df = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "Open": [10.0, 10.1],
            "High": [10.5, 10.6],
            "Low": [9.8, 9.9],
            "Close": [10.3, 10.4],
            "Volume": [100, 200],
        }
    )
    monkeypatch.setattr(svc, "_transform_data", lambda *a, **k: clean_df, raising=False)

    # Force _load_data to return 0 stored
    monkeypatch.setattr(svc, "_load_data", lambda *a, **k: 0, raising=False)

    out = await svc.run_pipeline("AAA", datetime(2024, 1, 1), datetime(2024, 1, 3), granularity="daily")
    assert out["status"] == "skipped"
    assert out["records_stored"] == 0
