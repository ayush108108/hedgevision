"""Datetime normalization utilities.

Provides a single public helper `normalize_datetime_iso` that converts a wide
range of date / datetime inputs into a canonical ISO8601 UTC string ending in
"Z". This is used before sending temporal filter values to Supabase so that
all queries use consistent, timezone‐aware boundaries.

Design goals:
1. Accept str | date | datetime | int/float (unix seconds) | None.
2. Treat date-only inputs ("2025-11-08") as midnight UTC of that date.
3. Preserve provided time component; if naive assume UTC.
4. For end boundaries you can optionally pass assume="end" to shift a date-only
   value to 23:59:59.999999 of that day (useful for inclusive end filters).
5. Always return RFC3339-compatible string with trailing 'Z'.

No external dependencies (avoids dateutil) – relies on stdlib heuristics.
"""

from __future__ import annotations

from datetime import datetime, date, timezone, timedelta
from typing import Any, Literal, Optional

ISO8601_DATE_LEN = 10  # len('YYYY-MM-DD')


def _coerce_to_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):  # date but not datetime
        return datetime(value.year, value.month, value.day)
    if isinstance(value, (int, float)):
        # treat as unix seconds
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # Replace trailing Z with +00:00 for fromisoformat compatibility
        if s.endswith("Z") and "+" not in s[-6:]:
            s_for_parse = s[:-1] + "+00:00"
        else:
            s_for_parse = s
        # If date-only, append time so fromisoformat handles it uniformly
        try:
            if len(s) == ISO8601_DATE_LEN and s.count("-") == 2 and "T" not in s:
                return datetime.fromisoformat(s + "T00:00:00+00:00")
            dt = datetime.fromisoformat(s_for_parse)
            return dt
        except Exception:
            # Final fallback – attempt parsing without timezone / with space
            try:
                if " " in s and "T" not in s:
                    # Replace space with T and retry
                    candidate = s.replace(" ", "T")
                    if candidate.endswith("Z") and "+" not in candidate[-6:]:
                        candidate = candidate[:-1] + "+00:00"
                    return datetime.fromisoformat(candidate)
            except Exception:
                return None
        return None
    # Unsupported type
    return None


def normalize_datetime_iso(
    value: Any,
    *,
    assume: Literal["start", "end"] = "start",
    end_inclusive: bool = True,
) -> Optional[str]:
    """Normalize an arbitrary date/datetime-like value to ISO8601 UTC string.

    Args:
        value: Input value (str/date/datetime/int/float/unix ts)
        assume: If value is date-only or naive, treat as start or end of day
        end_inclusive: When assume="end" and date-only, shift to 23:59:59.999999

    Returns:
        ISO8601 string like '2025-11-08T00:00:00Z' or None if unparseable.
    """
    dt = _coerce_to_datetime(value)
    if dt is None:
        return None

    # Attach UTC if naive
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        # Convert to UTC
        dt = dt.astimezone(timezone.utc)

    # If original looked like date-only and user wants end boundary
    if isinstance(value, str) and len(value.strip()) == ISO8601_DATE_LEN and assume == "end":
        if end_inclusive:
            dt = dt + timedelta(hours=23, minutes=59, seconds=59, microseconds=999999)
    return dt.isoformat().replace("+00:00", "Z")


__all__ = ["normalize_datetime_iso"]
