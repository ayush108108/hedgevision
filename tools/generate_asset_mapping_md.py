import os
import json

ROOT = os.path.dirname(os.path.dirname(__file__))
mapping_path = os.path.join(ROOT, "assets_mapping_yfi")
out_path = os.path.join(ROOT, "docs", "ASSET_MAPPING_YFI.md")

with open(mapping_path, "r", encoding="utf-8") as f:
    text = f.read()

# Robust parser: try strict JSON, else fallback to heuristic regex that extracts name/ticker pairs
assets = []
try:
    mapping = json.loads(text)
    assets = mapping.get("assets") if isinstance(mapping, dict) and mapping.get("assets") else []
except Exception:
    import re

    # Look for explicit name/ticker pairs where yfinance_ticker field may be spelled incorrectly
    # Pattern handles: "name": "Name", "yfinance_ticker": "TICKER"
    # Allow matching across multiple lines (DOTALL)
    pair_iter = re.finditer(r'"name"\s*:\s*"([^"]+)".*?"(?:yfinance_ticker|yfinance_tocker|yfinance)"\s*:\s*"([^"]+)"', text, re.DOTALL)
    for m in pair_iter:
        assets.append({"name": m.group(1).strip(), "yfinance_ticker": m.group(2).strip()})

    # If not found, try name without opening quote (common manual edit mistake)
    if not assets:
        pair_iter = re.finditer(r'"name"\s*:\s*([^\",\n]+)\s*,\s*"(?:yfinance_ticker|yfinance_tocker|yfinance)"\s*:\s*"([^"]+)"', text)
        for m in pair_iter:
            name = m.group(1).strip().strip('"')
            assets.append({"name": name, "yfinance_ticker": m.group(2).strip()})

lines = [
    "# Assets mapping (YFinance) — single source of truth",
    "",
    f"Generated from `assets_mapping_yfi` ({len(assets)} assets)",
    "",
    "| name | yfinance_ticker |",
    "|---|---|",
]

for a in assets:
    name = a.get("name") or a.get("asset") or ""
    y = a.get("yfinance_ticker") or a.get("yfinance") or a.get("yfinance_tocker") or ""
    lines.append(f"| {name} | {y} |")

with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print(f"Wrote {len(assets)} rows to {out_path}")