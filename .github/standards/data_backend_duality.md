# Data Backend Duality Standard

HedgeVision supports both `sqlite` and `supabase` backends. Changes must preserve correctness for the targeted mode(s).

## Rules

- Never assume Supabase-only availability in core code paths.
- Never assume SQLite-only behavior when API or pipeline logic can run in Supabase mode.
- If a change is intentionally backend-specific, document the untouched backend behavior explicitly.

## Validation

- For backend-sensitive changes, include proof for the affected backend mode.
- For shared-path changes, validate both modes or provide clear risk statement and follow-up gate.
