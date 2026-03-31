"""Compare current vs previous dual provider audit results.

Outputs a structured diff JSON at backend/output/dual_provider_comparison.json
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict

CUR_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "dual_provider_audit_results.json")
PREV_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "audit_results.json")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "dual_provider_comparison.json")


def load_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def key_subset(d: Dict[str, Any], keys: list[str]) -> Dict[str, Any]:
    return {k: d.get(k) for k in keys}


def main() -> None:
    cur = load_json(CUR_PATH)
    prev = load_json(PREV_PATH)

    cur_primary = cur.get("primary_result", {})
    cur_verifier = cur.get("verifier_result", {})

    prev_primary = prev.get("primary_result", prev)
    prev_verifier = prev.get("verifier_result", {})

    fields = ["issues", "recommendations", "severity", "summary"]

    diff = {
        "current": {
            "primary": key_subset(cur_primary, fields),
            "verifier": key_subset(cur_verifier, fields),
        },
        "previous": {
            "primary": key_subset(prev_primary, fields),
            "verifier": key_subset(prev_verifier, fields),
        },
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(diff, f, indent=2)
    print(f"Wrote comparison diff to {OUT_PATH}")


if __name__ == "__main__":
    main()
