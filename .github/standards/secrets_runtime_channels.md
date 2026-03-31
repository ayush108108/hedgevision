# Secrets and Runtime Channels Standard

## Secret handling

- Secrets must come from environment/config, never hardcoded.
- Never commit or log plaintext credentials.
- `.env.example` may include placeholders only.

## Runtime channels

- Avoid sending sensitive values to client-visible channels.
- Redact security-sensitive fields from logs and errors.
- Keep auth and key material out of telemetry payloads.

## Validation

- Any change touching auth, providers, or broker credentials must include leakage-path review.
