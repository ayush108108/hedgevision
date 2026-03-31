"""Sanitization utilities for LLM payload safety."""

from __future__ import annotations

import json
import re
from typing import Any

_SENSITIVE_RE = re.compile(
    r"(api[_-]?key|secret|token|password|authorization|credential|private[_-]?key|jwt)",
    re.IGNORECASE,
)

_URL_TOKEN_RE = re.compile(
    r"([?&])(apikey|api_key|token|key|auth)=([^&]+)",
    flags=re.IGNORECASE,
)

_KEYVAL_RE = re.compile(
    r"(api[_-]?key|token|secret|password|auth|jwt)\s*[:=]\s*([^\s,;]+)",
    flags=re.IGNORECASE,
)


def _sanitize_url_tokens(text: str) -> str:
    text = _URL_TOKEN_RE.sub(r"\1\2=***REDACTED***", text)
    return _KEYVAL_RE.sub(r"\1=***REDACTED***", text)


def sanitize_for_llm(payload: Any, max_chars: int = 20000) -> Any:
    """Sanitize potentially sensitive values before external LLM calls."""
    if isinstance(payload, dict):
        out: dict[str, Any] = {}
        for key, value in payload.items():
            if _SENSITIVE_RE.search(str(key)):
                out[key] = "***REDACTED***"
            else:
                out[key] = sanitize_for_llm(value, max_chars=max_chars)
        return out

    if isinstance(payload, list):
        return [sanitize_for_llm(item, max_chars=max_chars) for item in payload]

    if isinstance(payload, tuple):
        return tuple(sanitize_for_llm(item, max_chars=max_chars) for item in payload)

    if isinstance(payload, str):
        text = _sanitize_url_tokens(payload)
        if len(text) > max_chars:
            return f"{text[:max_chars]}... [TRUNCATED {len(text) - max_chars} chars]"
        return text

    # Ensure non-serializable objects do not crash upstream provider calls.
    try:
        json.dumps(payload)
        return payload
    except Exception:
        text = _sanitize_url_tokens(str(payload))
        if len(text) > max_chars:
            return f"{text[:max_chars]}... [TRUNCATED {len(text) - max_chars} chars]"
        return text
