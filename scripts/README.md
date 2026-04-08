# Scripts

Production scripts used by `make` targets and the data pipeline.

## Setup

| Script | Make Target | Purpose |
|--------|------------|---------|
| `setup/init_db.py` | `make db-init` | Create SQLite schema (safe to re-run) |

## Data

| Script | Make Target | Purpose |
|--------|------------|---------|
| `bootstrap_local_data.py` | `make db-bootstrap` | Seed 2 years of market data for 17 curated assets |
| `populate_sqlite_metrics.py` | (called by bootstrap) | Compute rolling risk metrics |

## Pipelines

| Script | Purpose |
|--------|---------|
| `pipelines/daily_eod_pipeline.py` | Daily end-of-day data sync + validation |
| `pipelines/analytics_computation_pipeline_v2.py` | Compute analytics (Supabase mode only) |
| `pipelines/populate_precomputed.py` | Generate precomputed data (Supabase mode only) |
