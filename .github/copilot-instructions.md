---
applyTo: "**"
---

# HedgeVision (stat-arb-v2) Agent Operating Rules

This repository is a **local-first statistical arbitrage platform**.

## Non-negotiable architecture facts

- Default runtime is local-first:
  - `DATA_BACKEND=sqlite`
  - `BROKER_BACKEND=paper`
  - `ENABLE_EXTERNAL_LLM=false`
- Supabase, external LLM providers, and CCXT live exchange are opt-in via explicit env vars.
- Core reusable business logic lives in `hedgevision/` and is consumed by API, CLI, and MCP.
- Backend API config is centralized in `backend/api/utils/config.py`.

## Safety and correctness rules

- Never assume only one data backend exists. Respect dual-mode behavior (`sqlite` and `supabase`).
- Do not introduce hidden live-trading behavior. Paper mode remains default unless user explicitly requests live trading.
- Never expose secrets or raw credentials in logs, responses, tests, or docs.
- Keep LLM payload sanitization in place (`hedgevision/security.py`).
- Avoid adding external dependencies unless clearly justified.

## Testing requirements

- For backend/data changes: run targeted `pytest` coverage for affected modules.
- For frontend changes: run `npm run lint` and relevant `vitest` tests in `frontend-v2/`.
- For runtime/reliability changes: provide explicit evidence (logs/output) before claiming readiness.

## Agent workflow

- Use the orchestrator and specialist agents in `.github/agents/`.
- Mandatory invocation order and quality gates are defined in:
  - `.github/standards/agent_hierarchy.md`
  - `.github/standards/agent_quality_gates.md`
