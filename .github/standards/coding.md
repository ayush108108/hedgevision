# Coding Standard (HedgeVision)

## Backend patterns

- Prefer routers → services → repositories/clients separation in `backend/api/`.
- Keep reusable logic in `hedgevision/` when shared across API/CLI/MCP.
- Centralize config usage via `backend/api/utils/config.py` where applicable.

## Frontend patterns

- Maintain strict TypeScript and explicit API contract handling.
- Keep state and data-fetching behavior predictable (Zustand + React Query patterns).

## Quality

- Write focused tests for changed behavior.
- Avoid broad refactors in bugfix tasks unless explicitly requested.
- Keep public interfaces backward-compatible unless change is intentional and documented.
