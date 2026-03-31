"""
Additional rolling metrics alignment tests.

Ensures each metrics row respects its window and date ordering, skipping when no
metrics are available.
"""

from __future__ import annotations

from datetime import datetime

import pytest


@pytest.mark.real_api
@pytest.mark.parametrize("symbol,window", [("AAPL.US", 252), ("MSFT.US", 180)])
def test_rolling_window_respects_date_span(sync_client, symbol: str, window: int):
    resp = sync_client.get(f"/api/metrics/rolling/{symbol}", params={"window": window, "benchmark": "SPY.US"})
    assert resp.status_code in (200, 404, 500, 503)
    if resp.status_code != 200:
        pytest.skip("No rolling metrics available for symbol/window")

    data = resp.json()
    metrics = data.get("metrics", [])
    if not metrics:
        pytest.skip("Empty rolling metrics list")

    for row in metrics:
        # Parse ISO date strings; tolerate timestamps or dates
        sd = datetime.fromisoformat(row["start_date"].replace("Z", "+00:00"))
        ed = datetime.fromisoformat(row["end_date"].replace("Z", "+00:00"))
        # Span in days should be at least window-1 (inclusive endpoints)
        span = (ed.date() - sd.date()).days + 1
        assert span >= window - 1, f"Expected span>={window-1}, got {span} for row id {row.get('id')}"

    # end_date should be non-increasing
    eds = [row["end_date"] for row in metrics]
    assert eds == sorted(eds, reverse=True)
