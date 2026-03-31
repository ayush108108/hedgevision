# Agent Hierarchy Standard (HedgeVision)

This defines mandatory orchestration order for all tasks.

## Mandatory invocation order

For any task (analysis, implementation, fix, refactor, test, deploy, docs):

1. `coordinator` preflight
2. `prompt-governor` prompt hardening
3. Exactly one primary specialist by domain
4. `qa-testing` validation for all change tasks (code/config/data/deploy)
5. `infrastructure-runtime` gate for runtime/deploy/reliability claims
6. `coordinator` final compliance verdict (`PASS` or `FAIL`)

## Primary specialist mapping

- Quant/statistical logic → `quant-research`
- Data ingestion/pipelines/backfills → `market-data-pipeline`
- FastAPI routes/services/repos → `backend-api`
- React/Vite UX/state/fetching → `frontend-trading-ui`
- Broker routing/execution safety → `broker-execution-risk`
- LLM/BYOK/provider routing/sanitization → `llm-byok-safety`
- MCP server and tool contract work → `mcp-tooling`
- Infra/CI/runtime/deploy plumbing → `infrastructure-runtime`

## Optional specialists (use only when needed)

- Observability/logging/SLO design → `observability`
- Secrets and security hardening → `security-secrets`
- External fact verification → `web-fact-gateway`

## Non-bypass rules

- Do not skip `prompt-governor` before specialist dispatch.
- Do not claim production readiness without validation evidence.
- Do not complete change tasks without `qa-testing` validation.
