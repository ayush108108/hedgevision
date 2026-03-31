# Pipeline Reliability Standard

This applies to ingestion, backfill, analytics, and precompute workflows.

## Rules

- Preserve idempotence where designed.
- Handle transient provider/network failures with controlled retry behavior.
- Keep stage gating explicit (especially mode-specific stage skips).
- Avoid hidden long-running startup work in API runtime.

## Operational checks

- For pipeline changes, include sample run output and failure-mode behavior.
- For schedule/automation changes, include expected trigger path and guardrails.
- Do not claim reliability without concrete evidence.
