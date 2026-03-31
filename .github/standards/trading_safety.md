# Trading Safety Standard

## Default safety posture

- `BROKER_BACKEND=paper` is default.
- No live execution side effects are allowed unless explicitly requested.

## Guardrails

- Order/execution paths must be clearly separated between paper and CCXT implementations.
- Test and demo scripts must not accidentally place live orders.
- Changes to broker routing require explicit risk note and validation evidence.

## Evidence requirements

- For broker-related changes, show proof of backend routing behavior.
- If CCXT path is touched, include safety checks and rollback guidance.
