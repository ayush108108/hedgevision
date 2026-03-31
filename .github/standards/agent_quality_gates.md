# Agent Quality Gates (HedgeVision)

Apply these to all change tasks.

## Pre-change gates

- Confirm target domain, blast radius, and data backend impact (`sqlite`, `supabase`, or both).
- Identify whether the change can affect trade execution path (paper vs CCXT).
- Validate config impact against `backend/api/utils/config.py` and env usage.

## Post-change gates

- Provide explicit file-level change summary.
- Provide verification evidence (tests/lint/runtime checks/log snapshots).
- Provide explicit architecture compliance verdict: `PASS` or `FAIL`.

## Required evidence by change type

- Backend/API/service/repository changes:
  - relevant `pytest` run + outcome
- Frontend changes:
  - `npm run lint` and related `vitest` run
- Pipeline/scheduling/runtime changes:
  - execution logs and failure-handling proof
- Security/secrets changes:
  - proof no secret leakage path introduced

## Hard-fail conditions

Mark final verdict `FAIL` if any of the below are true:

- Dual-backend behavior regresses without explicit acceptance.
- Live-trading risk introduced unintentionally.
- Secrets can be emitted to logs/responses.
- Claimed readiness lacks verification evidence.
