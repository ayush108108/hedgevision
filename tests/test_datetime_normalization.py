from datetime import datetime

import pytest

from backend.api.utils.datetime_normalization import normalize_datetime_iso


def test_date_only_start_boundary():
    assert normalize_datetime_iso("2025-11-08") == "2025-11-08T00:00:00Z"


def test_date_only_end_boundary():
    assert (
        normalize_datetime_iso("2025-11-08", assume="end")
        == "2025-11-08T23:59:59.999999Z"
    )


def test_naive_datetime_assumed_utc_preserved_time():
    dt = datetime(2025, 11, 8, 15, 0, 0)  # naive
    assert normalize_datetime_iso(dt) == "2025-11-08T15:00:00Z"


def test_tz_aware_converted_to_utc():
    # 2025-11-08 15:00:00+05:30 -> 09:30Z
    iso = normalize_datetime_iso("2025-11-08T15:00:00+05:30")
    assert iso == "2025-11-08T09:30:00Z"


def test_unix_timestamp_seconds():
    assert normalize_datetime_iso(0) == "1970-01-01T00:00:00Z"


def test_invalid_input_returns_none():
    assert normalize_datetime_iso("not a date") is None


# Parametrized fuzz around daylight saving transitions / offsets
@pytest.mark.parametrize(
    "input_str,expected_prefix",
    [
        ("2025-03-30T01:30:00+02:00", "2025-03-29"),  # Converts to prior day UTC
        ("2025-10-26T01:30:00+02:00", "2025-10-25"),  # DST style example (generic)
    ],
)
def test_tz_conversion_prefix_only(input_str, expected_prefix):
    iso = normalize_datetime_iso(input_str)
    assert iso is not None and iso.startswith(expected_prefix)
