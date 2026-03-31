# AI/ML Architecture (BYOK + MCP)

## Goals
- Keep quantitative logic independent from FastAPI runtime.
- Support Bring-Your-Own-Key (BYOK) model routing.
- Expose quant tools over MCP for assistant interoperability.
- Enforce schema-first contracts with strict Pydantic validation at core boundaries.
- Keep core quality gate at >=90% line coverage (`hedgevision` package).

## Core Components

### 1) `hedgevision` Library Package
- `hedgevision.core.market_intel`:
  - `fetch_market_data`
  - `compute_quant_metrics`
  - `analyze_sentiment`
  - `run_market_intel` (returns structured verdict payload)
- `hedgevision.pipelines.daily_eod`:
  - module wrapper for `scripts/pipelines/daily_eod_pipeline.py`

### 2) `LLMRouter` (Provider Abstraction)
Implemented in `hedgevision.llm.router.LLMRouter`.

Supported providers:
- `openai` (`OPENAI_API_KEY`)
- `anthropic` (`ANTHROPIC_API_KEY`)
- `ollama` (`OLLAMA_BASE_URL`)
- `cpu` (local CPU-bound deterministic model; optional `LOCAL_ML_BACKEND` and `LOCAL_ML_MODEL_PATH`)

Local-first policy:
- Default provider is local (`LLM_PROVIDER=ollama`) with `use_llm=false` unless explicitly enabled.
- External providers (`openai`, `anthropic`) are gated by `ENABLE_EXTERNAL_LLM=true`.
- CPU-local mode (`LLM_PROVIDER=cpu`) runs fully local inference with no network LLM calls.

All outbound prompts pass through:
- `SecureConfig` (`hedgevision.config.SecureConfig`)
- `sanitize_for_llm` (`hedgevision.security.sanitize_for_llm`)

### 3) MCP Server
Implemented in `hedgevision.mcp_server`.

Exposed tools:
- `hv_fetch_market_data`
- `hv_compute_quant_metrics`
- `hv_analyze_sentiment`

Example client question:
- "What is the 50-day SMA for BTC-USD?"
- Assistant resolves to `hv_compute_quant_metrics(ticker="BTC-USD")` and reads `sma_50`.

### 4) API Integration
- New endpoint: `GET /api/market-intel/verdict/{ticker}`
- Returns structured verdict for UI cards:
  - `stance`: bullish|bearish|neutral
  - `confidence`
  - `headline`
  - `rationale`
  - `model_version`
  - `model_provider`

### 5) Model Versioning
Database version isolation:
- New `MODEL_VERSION` env variable (default `prod-v1`)
- Writes/reads in Supabase client are scoped by model version when schema supports it.
- Migration script: `scripts/db/add_model_versioning.sql`
