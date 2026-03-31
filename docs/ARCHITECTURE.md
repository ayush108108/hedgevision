# System Architecture [Prod Level]

## High-Level Overview

```mermaid
graph TD
    User[User] -->|Browser| Frontend[Frontend V2 (React/Vite)]
    Frontend -->|REST API| Backend[FastAPI Backend]

    subgraph "Local-First Runtime"
        Backend -->|default| SQLite[(SQLite)]
        Backend -->|default| PaperBroker[Paper Broker]
        Backend -->|default| RulesEngine[Rule-Based Market Intel]
        CLI[hedgevision-cli] -->|sync/intel/mcp/broker| BackendCore[hedgevision core package]
        MCP[MCP Server] -->|tools| AIClient[MCP Clients]
    end

    subgraph "Optional External Integrations"
        Backend -->|opt-in| Supabase[(Supabase/Postgres)]
        Backend -->|opt-in| ExtLLM[OpenAI / Anthropic]
        Backend -->|opt-in| CCXT[CCXT Exchange Broker]
    end

    DataSrc[Market Data: yfinance / exchange feeds] --> BackendCore
```

## Core Principles

- Local-first by default (`DATA_BACKEND=sqlite`, `BROKER_BACKEND=paper`, `ENABLE_EXTERNAL_LLM=false`).
- External services are explicit opt-ins (Supabase, OpenAI/Anthropic, CCXT live exchange).
- Quant/business logic is reusable from CLI/API/MCP via `hedgevision/` package.

## Components

### 1) Frontend (`frontend-v2/`)
- React 18 + Vite + TypeScript
- Zustand (including persisted BYOK settings)
- Calls backend REST endpoints

### 2) Backend API (`backend/api/`)
- FastAPI routing, middleware, health/readiness checks
- Uses config-driven backend mode:
  - SQLite mode: local DB path + lightweight startup
  - Supabase mode: Supabase client for production/shared DB workflows

### 3) Core Library (`hedgevision/`)
- `hedgevision.core.market_intel`: quant metrics + structured verdicts
- `hedgevision.llm.router`: provider abstraction (OpenAI, Anthropic, Ollama)
- `hedgevision.broker`: paper broker + CCXT adapter
- `hedgevision.pipelines.daily_eod`: CLI wrapper for daily pipeline
- `hedgevision.mcp_server`: MCP tool server exposing quant tools

### 4) Data/Pipelines (`scripts/`)
- Daily EOD ingestion pipeline with validation gates
- In SQLite mode, Supabase-only heavy subprocess stages are skipped
- In Supabase mode, full analytics/precompute stages run

## Integration Surface

- API endpoint: `GET /api/market-intel/verdict/{ticker}` (structured verdict)
- API endpoint: `GET /api/broker/quote/{symbol}` (paper/CCXT quote)
- CLI:
  - `hedgevision-cli onboard`
  - `hedgevision-cli sync`
  - `hedgevision-cli intel <ticker>`
  - `hedgevision-cli broker-quote <symbol>`
  - `hedgevision-cli mcp`

Onboarding:
- CLI wizard: interactive env setup for local-first runtime.
- UI wizard: `/onboarding` stepper for backend/model/broker selection.
- Model runtimes include `rules`, `ollama`, and `cpu` (CPU-bound local model path).

## Operational Hardening Notes

- Heavy screener recomputation is disabled on API startup by default.
- Optional background worker / CI workflow handles recompute.
- Model-version isolation supported via `MODEL_VERSION` for production safety.
