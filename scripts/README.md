# Scripts & Automation Index

Last updated: 2025-11-14

This index organizes every executable script in the repository so you always know where to look for a workflow entry point and how to run it safely.

## Directory Map

| Location | Purpose | Notes |
| --- | --- | --- |
| `scripts/pipelines/` | Production-grade data pipelines (daily EOD, 4h incremental, analytics computation, precomputation). | Mirrors scheduled GitHub Actions; see `operations/pipelines.md` for orchestration details. |
| `scripts/db/` | Database inspection helpers (schema queries, sample pulls). | Read-only utilities; extend here for future DB tooling. |
| `scripts/*.py` | Health checks, validation guards, orchestration wrappers (`preflight_check.py`, `run_population_workflow.py`, etc.). | Keep these small and composable; add docs inline if behavior is non-obvious. |
| `backend/scripts/` | Legacy backend-specific jobs pending migration. | Treat as read-only; move active scripts into `scripts/` when refactoring. Document moves in this file. |
| `backend/archived_scripts/` | Historical or deprecated routines retained for reference. | Read-only history; restore from Git history if a legacy routine is required. |

## Featured Utilities
- `python backend/scripts/bootstrap_assets.py --presets all --commit` – Upsert the full cross-asset universe (equities, ETFs, FX, commodities, crypto) into Supabase. Omit `--commit` for a dry-run, use `--presets equities,index_etf`, or `--presets pilot` for the validation subset.
  - Requires `SUPABASE_SERVICE_KEY` (preferred) or `SUPABASE_KEY`; the script auto-detects the primary identifier column (`symbol` or `yfinance_ticker`) and will mirror the new assets accordingly.
- `python scripts/db/update_pilot_tickers.py --commit` – Normalize yfinance tickers for the pilot basket (e.g., `JPY=X`, `CL=F`, `BTC-USD`) before running backfills.
- `python scripts/preflight_check.py` – Verify environment configuration before pipeline runs.
- `python scripts/run_population_workflow.py` – One-shot orchestration for correlation & cointegration precomputation once analytics logic is validated.

## Usage Guidelines
1. **Activate the repo virtual environment** (`python -m venv .venv` → `.\.venv\Scripts\activate`) before running Python-based scripts.
2. **Dry run first** when available (look for `--dry-run` flags). For pipelines, start with small date ranges.
3. **Log outputs** to `backend/output/` or a dedicated location under `scripts/output/`. Generated artifacts should be gitignored (see `.gitignore`).
4. **Document changes**: when a script gains new parameters or functionality, update this file and the relevant operations doc.

## Migration Checklist
- When promoting a script from `backend/scripts/` into the primary `scripts/` tree:
  - Ensure imports are relative-safe (no implicit `backend.` dependencies).
  - Update `tests/` or create coverage to protect behavior.
  - Remove stale duplicates from `backend/scripts/` and note the change in `CHANGELOG.md`.

By keeping this index updated, the repository maintains a reliable map of operational tooling alongside the audit blueprint.
