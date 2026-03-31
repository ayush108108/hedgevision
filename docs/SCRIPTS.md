# Scripts & Tools [Adhoc Level]

The `scripts/` directory contains essential utilities for data management, pipeline execution, and system maintenance. These scripts are typically run ad-hoc by developers or scheduled via cron/orchestrators in production.

**Note**: Always run these scripts with the backend virtual environment active.

## 📂 Data Ingestion & Pipelines

| Script | Information |
| :--- | :--- |
| `bootstrap_assets_timescale.py` | **Major**: Initializes the asset universe and fetching initial historical data for TimescaleDB. |
| `master_all_time_workflow.py` | Orchestrates the full historical data fetch and calculation workflow. |
| `run_population_workflow.py` | Runs the population routine to fill the database with recent data. |
| `extract_assets_list.py` | Utility to extract/update the list of assets being tracked. |
| `validate_yfinance_tickers.py` | Verifies that the configured tickers are valid and fetchable from YFinance. |

## 📊 Analytics & Computation

| Script | Information |
| :--- | :--- |
| `precompute_correlations.py` | Calculates valid correlation pairs between assets. Validates statistical significance. |
| `populate_cointegration.py` | Runs co-integration tests (Engle-Granger, etc.) on pairs and stores results. |
| `compute_rolling_metrics_standalone.py` | Computes rolling window metrics (Z-Score, Spread) for pairs. |
| `comprehensive_multi_tier_eda.py` | Runs exploratory data analysis and generates reports/metrics. |

## 🛠 Maintenance & Utility

| Script | Information |
| :--- | :--- |
| `check_db_status.py` | **Critical**: Checks connectivity and health of the Supabase database. |
| `truncate_db.py` | **Danger**: Wipes specific tables in the database. Use with caution. |
| `quick_cleanup_db.py` | Lighter version of truncate, often for removing invalid entries. |
| `cleanup_disabled_assets.py` | Removes data related to assets that have been disabled in configuration. |
| `apply_schema.py` | Applies SQL schema changes to the database. |
| `simple_validation.py` | Runs basic sanity checks on the data integrity. |

## 🧪 Testing & Validation

| Script | Information |
| :--- | :--- |
| `preflight_check.py` | Runs a suite of checks before a deployment or major run. |
| `smoke_import.py` | fast check to ensure imports and basic config work. |
| `test_ci_workflows.py` | Tests CI/CD pipeline steps locally. |

## 🤖 Agents & Demos

These scripts demonstrate or run specific AI agent workflows.

| Script | Information |
| :--- | :--- |
| `backend/run_market_intel_demo.py` | Runs the Market Intelligence pipeline (optionally with LLMs) for a specific ticker. usage: `python backend/run_market_intel_demo.py --ticker AAPL`. |

## Usage Example

**Bootstrapping the database:**
```bash
# 1. Activate environment
source ../backend/.venv/bin/activate

# 2. Check DB
python ../backend/check_db_status.py

# 3. Bootstrap (fetch initial data)
python bootstrap_assets_timescale.py
```

## 🧰 Tools

The `tools/` directory contains helper scripts for documentation generation and other non-critical tasks.

| Tool | Information |
| :--- | :--- |
| `generate_asset_mapping_md.py` | Generates a markdown file listing all assets and their mapping (from `assets_mapping_yfi`). useful for updating documentation. |
