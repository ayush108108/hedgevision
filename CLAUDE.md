# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

HedgeVision (stat-arb-v2) is a quantitative trading platform for statistical arbitrage. It is **local-first by default** — SQLite, paper broker, and rule-based intelligence engine run out of the box. Supabase (Postgres), external LLMs (OpenAI/Anthropic/Ollama), and live exchange brokers (CCXT) are explicit opt-ins configured via environment variables.

## Common Commands

### Backend (from repo root)

```bash
# Install Python deps
pip install -e ".[all]"  # installs hedgevision + all optional deps in editable mode

# Run backend API server
uvicorn backend.api.main:app --reload

# Run daily data pipeline
python scripts/pipelines/daily_eod_pipeline.py
# or via CLI
hedgevision-cli sync [--dry-run]
```

### Frontend (from frontend-v2/)

```bash
npm install
npm run dev       # dev server on port 3000
npm run build
npm run lint
npm test          # vitest
npm run test:coverage
```

### Tests

```bash
# Run all Python tests with coverage
pytest

# Run a single test file
pytest tests/test_analytics_service_unit.py

# Run tests by marker
pytest -m unit
pytest -m integration

# Frontend tests
cd frontend-v2 && npx vitest run src/pages/__tests__/SomePage.test.tsx
```

### Linting & Formatting

```bash
# Python
black --line-length 100 .
isort --profile black --line-length 100 .
flake8 .
mypy hedgevision/

# Frontend (from frontend-v2/)
npm run lint

# Run all pre-commit hooks
pre-commit run --all-files
```

## Architecture

### Three-Layer Structure

1. **`hedgevision/`** — Core installable package. Contains Pydantic models, LLM router, broker abstraction, market intelligence engine, MCP server, CLI, and pipeline wrappers. This is the reusable business logic consumed by API, CLI, and MCP.

2. **`backend/api/`** — FastAPI REST API. Routers → Services → Repositories/Clients. 18 routers, middleware stack (security headers → rate limiting → CORS → gzip). Config in `backend/api/utils/config.py` loads env vars and controls dual-backend mode.

3. **`frontend-v2/`** — React 18 + Vite + TypeScript + TailwindCSS. State via Zustand (3 stores: ticker, BYOK, onboarding — latter two persisted to localStorage). Data fetching via @tanstack/react-query + Axios. All pages lazy-loaded.

### Data Backend Duality

The `DATA_BACKEND` env var (`sqlite` or `supabase`) controls which storage layer is used. This switch propagates through config, services, and pipelines. In SQLite mode, analytics-heavy pipeline stages and Supabase-only features are skipped. Always test both paths when modifying data access code.

### Key Config Files

- `backend/api/utils/config.py` — Central backend config (all env vars, defaults, dual-backend logic)
- `hedgevision/config.py` — `SecureConfig` Pydantic model for core package settings
- `config/asset_universe_master.yaml` — Master list of all tradeable assets (crypto + equities)

### Pipeline Architecture

`scripts/pipelines/daily_eod_pipeline.py` runs a 4-stage pipeline with validation gates:
1. Raw data ingestion (yfinance, batched)
2. Data quality validation (completeness, freshness, coverage checks)
3. Analytics computation (Supabase mode only)
4. Precomputed data generation (Supabase mode only)

Stages 3-4 are skipped when `DATA_BACKEND=sqlite`.

### BYOK (Bring Your Own Key) Model

LLM provider is configurable: `rules` (default, no LLM), `cpu`, `ollama`, `openai`, `anthropic`. The frontend persists the user's choice in localStorage via the `byokStore`. The backend's `LLMRouter` in `hedgevision/llm/router.py` handles provider dispatch. All outbound LLM payloads are sanitized via `hedgevision/security.py` (API keys, tokens, secrets are redacted).

### Broker Abstraction

`hedgevision/broker/router.py` factory returns either `PaperBroker` (simulated) or `CCXTBroker` (real exchange) based on `BROKER_BACKEND` env var.

## Code Conventions

- **Python**: Black (line-length 100), isort (profile black), flake8, mypy strict. Target Python 3.10+.
- **Frontend**: ESLint + Prettier, TypeScript strict mode, ES2020 target.
- **Pydantic models** in `hedgevision/models.py` use `StrictModel` (extra="forbid", finite-float validation). Follow this pattern for new models.
- **Test markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.real_api`, etc. Mark tests appropriately.
- **Coverage**: pytest enforces `--cov-fail-under=90` on the `hedgevision/` package.
- **asyncio**: `asyncio_mode = auto` in pytest — async test functions are automatically detected.
- **Model versioning**: `MODEL_VERSION` env var scopes DB writes for production safety.

## Environment Setup

Copy `backend/api/.env.example` to `backend/api/.env`. Minimum local config:

```ini
DATA_BACKEND=sqlite
DB_PATH=backend/prices.db
ENABLE_EXTERNAL_LLM=false
BROKER_BACKEND=paper
```

Frontend env at `frontend-v2/.env.local`:
```ini
VITE_API_BASE_URL=http://localhost:8000
```
