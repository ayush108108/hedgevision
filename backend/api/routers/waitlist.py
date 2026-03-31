from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from api.utils.config import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/waitlist", tags=["waitlist"])


class WaitlistSignupRequest(BaseModel):
    """Email capture payload for feature waitlists and release notifications."""

    email: EmailStr
    source_page: str = Field(..., min_length=1, max_length=100)
    source_label: Optional[str] = Field(default=None, max_length=150)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WaitlistSignupResponse(BaseModel):
    """Response returned after attempting to capture a waitlist email."""

    status: str
    message: str
    storage: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_string(value: Optional[str], fallback: str) -> str:
    cleaned = (value or fallback).strip().lower().replace("_", "-")
    return cleaned[:100] or fallback


def _compact_dict(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None}


def _candidate_tables() -> list[str]:
    env_tables = os.getenv("WAITLIST_TABLE_NAMES") or os.getenv("WAITLIST_TABLE_NAME")
    if env_tables:
        return [table.strip() for table in env_tables.split(",") if table.strip()]

    return [
        "waitlist_signups",
        "email_signups",
        "email_waitlist",
        "newsletter_signups",
        "waitlist",
        "subscribers",
    ]


def _candidate_payloads(request: WaitlistSignupRequest) -> list[dict[str, Any]]:
    email = str(request.email).strip().lower()
    created_at = _utc_now_iso()
    source_page = _clean_string(request.source_page, "unknown")
    source_label = request.source_label.strip()[:150] if request.source_label else None
    metadata = request.metadata or {}

    return [
        _compact_dict(
            {
                "email": email,
                "source_page": source_page,
                "source_label": source_label,
                "metadata": metadata,
                "created_at": created_at,
            }
        ),
        _compact_dict(
            {
                "email": email,
                "source": source_page,
                "label": source_label,
                "metadata": metadata,
                "created_at": created_at,
            }
        ),
        _compact_dict(
            {
                "email_address": email,
                "source_page": source_page,
                "source_label": source_label,
                "metadata": metadata,
                "created_at": created_at,
            }
        ),
        {"email": email, "created_at": created_at},
        {"email_address": email, "created_at": created_at},
    ]


def _is_duplicate_error(message: str) -> bool:
    lowered = message.lower()
    return any(
        token in lowered
        for token in (
            "duplicate key",
            "already exists",
            "unique constraint",
            "violates unique",
        )
    )


def _get_supabase_client() -> Any | None:
    try:
        from supabase import create_client
    except ImportError:
        logger.info("Waitlist signup fallback active: supabase package unavailable")
        return None

    url = config.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = (
        config.get("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_SERVICE_KEY")
        or config.get("SUPABASE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
        or config.get("SUPABASE_ANON_KEY")
    )

    if not url or not key:
        return None

    try:
        return create_client(url, key)
    except Exception as exc:
        logger.warning("Failed to initialize Supabase waitlist client: %s", exc)
        return None


def _try_supabase_store(request: WaitlistSignupRequest) -> tuple[str, str] | None:
    client = _get_supabase_client()
    if client is None:
        return None

    errors: list[str] = []
    for table in _candidate_tables():
        for payload in _candidate_payloads(request):
            try:
                response = client.table(table).insert(payload).execute()
                if response is not None:
                    logger.info(
                        "Stored waitlist signup for %s in Supabase table '%s'",
                        request.email,
                        table,
                    )
                    return "created", f"supabase:{table}"
            except Exception as exc:
                message = str(exc)
                if _is_duplicate_error(message):
                    logger.info(
                        "Duplicate waitlist signup for %s detected in table '%s'",
                        request.email,
                        table,
                    )
                    return "duplicate", f"supabase:{table}"
                errors.append(f"{table}: {message}")

    if errors:
        logger.warning("Supabase waitlist write attempts failed: %s", " | ".join(errors[:6]))
    return None


def _ensure_sqlite_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS waitlist_signups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            source_page TEXT NOT NULL,
            source_label TEXT,
            metadata_json TEXT,
            created_at TEXT NOT NULL
        )
        """
    )


def _store_sqlite_waitlist(request: WaitlistSignupRequest) -> tuple[str, str]:
    db_path = Path(str(config.get("DB_PATH") or "backend/prices.db"))
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path, timeout=5.0) as connection:
        _ensure_sqlite_table(connection)
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO waitlist_signups (
                email,
                source_page,
                source_label,
                metadata_json,
                created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(request.email).strip().lower(),
                _clean_string(request.source_page, "unknown"),
                request.source_label.strip()[:150] if request.source_label else None,
                json.dumps(request.metadata or {}, sort_keys=True),
                _utc_now_iso(),
            ),
        )
        connection.commit()

        if cursor.rowcount == 0:
            return "duplicate", "sqlite:waitlist_signups"

    logger.info("Stored waitlist signup for %s in SQLite", request.email)
    return "created", "sqlite:waitlist_signups"


def _message_for_status(result_status: str) -> str:
    if result_status == "duplicate":
        return "You’re already on the list — we’ll keep you posted."
    return "Thanks — you’re on the waitlist now."


@router.post("", response_model=WaitlistSignupResponse, status_code=status.HTTP_201_CREATED)
async def join_waitlist(payload: WaitlistSignupRequest) -> WaitlistSignupResponse:
    """Capture waitlist signups for unreleased product features."""

    supabase_result = _try_supabase_store(payload)
    if supabase_result is not None:
        result_status, storage = supabase_result
        return WaitlistSignupResponse(
            status=result_status,
            message=_message_for_status(result_status),
            storage=storage,
        )

    if str(config.get("DATA_BACKEND", "sqlite")).lower() == "sqlite":
        result_status, storage = _store_sqlite_waitlist(payload)
        return WaitlistSignupResponse(
            status=result_status,
            message=_message_for_status(result_status),
            storage=storage,
        )

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Waitlist storage is not available right now.",
    )
