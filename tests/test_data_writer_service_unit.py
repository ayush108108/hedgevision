from __future__ import annotations

import types
from typing import Any, List, Optional
import pandas as pd
import pytest
import importlib
import sys
from pathlib import Path


class SupabaseTableStub:
    def __init__(self, parent: SupabaseClientStub, name: str):
        self.parent = parent
        self.name = name
        self._batch = None

    def upsert(self, batch, on_conflict=None):  # noqa: D401
        # capture and return self for chaining .execute()
        self._batch = list(batch)
        self.parent.last_table = self.name
        self.parent.last_upserted_rows = self._batch
        self.parent.last_on_conflict = on_conflict
        return self

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def gte(self, *args, **kwargs):
        return self

    def lte(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        # Return empty data for select queries, batch data for upserts
        if self._batch is not None:
            return types.SimpleNamespace(data=self._batch)
        return types.SimpleNamespace(data=[])


class SupabaseClientStub:
    def __init__(self):
        self.last_table: Optional[str] = None
        self.last_upserted_rows: Optional[List[Any]] = None
        self.last_on_conflict: Optional[str] = None

    def table(self, name: str):
        return SupabaseTableStub(self, name)


def _get_data_writer_class():
    backend_path = Path(__file__).parent.parent / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    return importlib.import_module("api.services.data_writer_service").DataWriter


@pytest.fixture()
def writer_stub(monkeypatch):
    """Provide a DataWriter with stubbed supabase and asset id resolution."""
    DataWriter = _get_data_writer_class()
    w = DataWriter()
    # Force supabase backend so we exercise the Supabase upsert path with our stub
    monkeypatch.setattr(w, "backend", "supabase", raising=False)
    # replace real supabase client with stub
    client = SupabaseClientStub()
    monkeypatch.setattr(w, "supabase", client, raising=False)
    # resolve any symbol to fixed id=42 (accept provider kwarg)
    monkeypatch.setattr(w, "_get_asset_id", lambda symbol, provider="yfinance": 42, raising=False)
    return w


@pytest.mark.unit
def test_store_data_happy_path(writer_stub):
    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "Open": [10.0, 10.5],
            "High": [11.0, 11.1],
            "Low": [9.9, 10.4],
            "Close": [10.5, 11.0],
            "Volume": [1000, 1100],
        }
    )

    writer_stub.store_data("TEST", df)

    client: SupabaseClientStub = writer_stub.supabase  # type: ignore[assignment]
    assert client.last_table == "price_history"
    assert client.last_upserted_rows is not None
    assert isinstance(client.last_upserted_rows, list)
    assert len(client.last_upserted_rows) == 2
    # ensure transformed payload fields present
    row = client.last_upserted_rows[0]
    assert set(["asset_id", "timestamp", "open", "high", "low", "close", "source"]) <= set(row.keys())


@pytest.mark.unit
def test_store_data_filters_invalid_rows(writer_stub):
    # second row invalid: low > high, should be filtered out
    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "Open": [10.0, 10.5],
            "High": [11.0, 10.6],
            "Low": [9.9, 10.7],  # invalid
            "Close": [10.5, 10.55],
            "Volume": [1000, 1100],
        }
    )

    writer_stub.store_data("TEST", df)

    client: SupabaseClientStub = writer_stub.supabase  # type: ignore[assignment]
    # only the first valid row should be upserted
    assert client.last_upserted_rows is not None
    assert len(client.last_upserted_rows) == 1


@pytest.mark.unit
def test_store_data_missing_columns_noop(writer_stub):
    # Missing 'Open' column -> should log and return without calling upsert
    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-01"]),
            "High": [11.0],
            "Low": [9.9],
            "Close": [10.5],
            "Volume": [1000],
        }
    )

    writer_stub.store_data("TEST", df)
    client: SupabaseClientStub = writer_stub.supabase  # type: ignore[assignment]
    assert client.last_upserted_rows is None


@pytest.mark.unit
def test_store_hourly_prices_happy_path(writer_stub):
    df = pd.DataFrame(
        {
            "Timestamp": pd.to_datetime(["2024-01-01 10:00", "2024-01-01 11:00"]),
            "Open": [10.0, 10.2],
            "High": [10.5, 10.6],
            "Low": [9.8, 10.1],
            "Close": [10.3, 10.4],
            "Volume": [500, 600],
        }
    )

    writer_stub.store_hourly_prices("TEST", df)

    client: SupabaseClientStub = writer_stub.supabase  # type: ignore[assignment]
    assert client.last_table == "price_history"
    assert client.last_upserted_rows is not None
    assert len(client.last_upserted_rows) == 2


@pytest.mark.unit
def test_store_data_accepts_timestamp_and_lowercase_ohlcv(writer_stub):
    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2024-01-01 12:34:00"]),
            "open": [12.0],
            "high": [12.5],
            "low": [11.5],
            "close": [12.2],
            "volume": [200],
        }
    )

    # Should accept 'timestamp' and lowercase OHLCV names and map/normalize them
    writer_stub.store_data("TEST", df)

    client: SupabaseClientStub = writer_stub.supabase
    assert client.last_table == "price_history"
    assert client.last_upserted_rows is not None
    assert len(client.last_upserted_rows) == 1

    row = client.last_upserted_rows[0]
    # The writer should normalize columns to the expected titlecase keys
    assert set(["asset_id", "timestamp", "open", "high", "low", "close"]) <= set(row.keys())
    # timestamp should be present and of type pd.Timestamp or ISO string
    assert row["timestamp"] is not None


@pytest.mark.unit
def test_store_multiple_symbols_bulk_upsert(writer_stub):
    data = {
        "AAA": pd.DataFrame(
            {
                "Date": pd.to_datetime(["2024-01-01"]),
                "Open": [10],
                "High": [11],
                "Low": [9.5],
                "Close": [10.5],
                "Volume": [1000],
            }
        ),
        "BBB": pd.DataFrame(
            {
                "Date": pd.to_datetime(["2024-01-01"]),
                "Open": [20],
                "High": [21],
                "Low": [19.5],
                "Close": [20.5],
                "Volume": [2000],
            }
        ),
    }

    result = writer_stub.store_multiple_symbols(data)

    client: SupabaseClientStub = writer_stub.supabase  # type: ignore[assignment]
    assert client.last_table == "price_history"
    assert client.last_upserted_rows is not None
    assert len(client.last_upserted_rows) == 2  # Both symbols' data
    # Check that results dict has entries for both symbols
    assert "AAA" in result
    assert "BBB" in result
    assert result["AAA"] == 1  # One row inserted for AAA
    assert result["BBB"] == 1  # One row inserted for BBB
