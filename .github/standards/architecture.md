# Architecture Standard (HedgeVision)

## System layers

1. Core library (`hedgevision/`): domain models, broker abstraction, LLM router, MCP server, pipeline wrappers.
2. API (`backend/api/`): routers → services → repositories/clients.
3. Frontend (`frontend-v2/`): React app consuming API.
4. Pipelines (`scripts/pipelines/`): ingestion, validation, analytics, precompute.

## Core principles

- Local-first by default.
- External integrations are explicit opt-ins.
- Keep business logic reusable through `hedgevision/` package.

## Data backend duality

- `DATA_BACKEND=sqlite`:
  - prioritize local operation and fast startup.
  - skip Supabase-only heavy analytics stages when required by pipeline design.
- `DATA_BACKEND=supabase`:
  - enable shared production-like workflows and full analytics stages.

## Broker and execution safety

- Default broker is paper mode.
- Live broker (`ccxt`) must be explicit and guarded.
- Avoid code paths that can place unintended live orders.

## LLM/BYOK model

- Provider options include `rules`, `cpu`, `ollama`, `openai`, `anthropic`.
- External providers are opt-in.
- Outbound payloads must remain sanitized.

## Configuration

- Backend config source of truth: `backend/api/utils/config.py`.
- Avoid ad hoc environment reads in scattered modules when centralized config is available.
