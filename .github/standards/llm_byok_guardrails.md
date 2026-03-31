# LLM BYOK Guardrails

## Provider model

Supported providers include: `rules`, `cpu`, `ollama`, `openai`, `anthropic`.

## Rules

- External LLM usage must remain opt-in via config.
- Keep payload and log sanitization active.
- Never print API keys/tokens/secrets in logs, traces, or responses.
- Respect user/provider selection and avoid silent provider switching.

## Validation

- For LLM routing changes, show provider selection behavior and safe fallback.
- Confirm sanitization remains active for outbound provider requests.
