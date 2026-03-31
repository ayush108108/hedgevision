"""
Generate a timestamped markdown summary for the latest dual-provider audit.
Reads `backend/output/dual_provider_audit_results.json` and writes `backend/output/audit_summary_<generated_at>.md`.
If `generated_at` is unavailable, uses current UTC timestamp.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict

AUDIT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "dual_provider_audit_results.json")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")


def ts_from_generated_at(d: Dict[str, Any]) -> str:
    ga = d.get("generated_at")
    if isinstance(ga, str) and len(ga) >= 19:
        # Expect YYYY-MM-DDTHH:MM:SSZ
        # Normalize to yyyymmddTHHMMSSZ
        try:
            date = ga.replace("-", "").replace(":", "")
            date = date.replace("+00:00", "Z")
            # e.g., 2025-11-12T05:56:28Z -> 20251112T055628Z
            return f"{date[0:8]}T{date[9:15]}Z"
        except Exception:
            pass
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def main() -> None:
    if not os.path.exists(AUDIT_PATH):
        raise SystemExit(f"Audit file not found: {AUDIT_PATH}")
    with open(AUDIT_PATH, "r", encoding="utf-8") as f:
        d = json.load(f)

    ts = ts_from_generated_at(d)
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f"audit_summary_{ts}.md")

    selected = d.get("selected_snippets", []) or []
    cfg = d.get("config", {})
    primary = d.get("primary_result", {}) or {}
    verifier = d.get("verifier_result", {}) or {}

    def n_issues(obj):
        if isinstance(obj, dict) and isinstance(obj.get("issues"), list):
            return len(obj.get("issues"))
        return "n/a"

    summary = []
    summary.append("# Dual Provider Audit Summary\n")
    summary.append(f"Generated: {d.get('generated_at', 'unknown')}\n")
    summary.append(f"RAG used: {cfg.get('rag_used')} | Model: {cfg.get('embedding_model')} | top_k: {cfg.get('top_k')}\n")
    summary.append(f"Snippets selected: {len(selected)} | Revision performed: {d.get('revision_performed')}\n\n")
    summary.append("## Issue counts\n")
    summary.append(f"- Primary issues: {n_issues(primary)}\n")
    summary.append(f"- Verifier issues: {n_issues(verifier)}\n\n")

    # Optional short lists
    def collect_summaries(items):
        out = []
        if isinstance(items, list):
            for it in items[:10]:  # cap to 10
                if isinstance(it, dict):
                    title = it.get("title") or it.get("id") or it.get("summary") or str(it)[:100]
                else:
                    title = str(it)[:100]
                out.append(f"- {title}")
        return out

    if isinstance(primary, dict) and isinstance(primary.get("issues"), list):
        summary.append("### Primary: top issues\n")
        summary.extend(collect_summaries(primary.get("issues")))
        summary.append("\n")

    if isinstance(verifier, dict) and isinstance(verifier.get("issues"), list):
        summary.append("### Verifier: top issues\n")
        summary.extend(collect_summaries(verifier.get("issues")))
        summary.append("\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(summary))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
