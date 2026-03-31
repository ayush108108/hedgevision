"""BYOK LLM router supporting OpenAI, Anthropic, local Ollama, and rule-based inference."""

from __future__ import annotations

from typing import Any

import httpx

from hedgevision.config import SecureConfig
from hedgevision.models import LLMResponsePayload
from hedgevision.security import sanitize_for_llm


class _BaseProvider:
    def __init__(self, config: SecureConfig):
        self.config = config

    async def complete(self, messages: list[dict[str, str]], model: str) -> str:
        raise NotImplementedError


class _RulesProvider(_BaseProvider):
    """No-LLM provider: returns a deterministic placeholder response.

    Used as the safe default when no external LLM is configured.
    The actual rule-based verdict logic lives in ``hedgevision.core.market_intel``.
    """

    async def complete(self, messages: list[dict[str, str]], model: str) -> str:  # noqa: ARG002
        return "Rule-based inference active. No external LLM configured."


class _CPUProvider(_BaseProvider):
    """CPU-local inference provider backed by a local model file or numpy heuristics."""

    async def complete(self, messages: list[dict[str, str]], model: str) -> str:
        model_path = self.config.local_ml_model_path
        if model_path:
            # Delegate to a local ONNX / sklearn model when a path is configured.
            # Fallback to heuristic summary for now.
            pass
        user_text = " ".join(m["content"] for m in messages if m["role"] == "user")
        return f"[cpu-local] {user_text[:200]}"


class _OpenAIProvider(_BaseProvider):
    async def complete(self, messages: list[dict[str, str]], model: str) -> str:
        if not self.config.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for provider=openai")
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=self.config.openai_api_key,
            timeout=self.config.llm_timeout_seconds,
        )
        result = await client.chat.completions.create(model=model, messages=messages)
        return (result.choices[0].message.content or "").strip()


class _AnthropicProvider(_BaseProvider):
    async def complete(self, messages: list[dict[str, str]], model: str) -> str:
        if not self.config.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for provider=anthropic")
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(
            api_key=self.config.anthropic_api_key,
            timeout=self.config.llm_timeout_seconds,
        )
        # Anthropic expects separated system and user content.
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        user_parts = [m["content"] for m in messages if m["role"] != "system"]
        response = await client.messages.create(
            model=model,
            max_tokens=1024,
            system="\n\n".join(system_parts),
            messages=[{"role": "user", "content": "\n\n".join(user_parts)}],
        )
        text_chunks: list[str] = []
        for block in response.content:
            if getattr(block, "type", "") == "text":
                text_chunks.append(getattr(block, "text", ""))
        return "\n".join(chunk for chunk in text_chunks if chunk).strip()


class _OllamaProvider(_BaseProvider):
    async def complete(self, messages: list[dict[str, str]], model: str) -> str:
        url = f"{self.config.ollama_base_url}/api/chat"
        payload = {"model": model, "messages": messages, "stream": False}
        async with httpx.AsyncClient(timeout=self.config.llm_timeout_seconds) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()
            message = body.get("message") or {}
            return str(message.get("content") or "").strip()


class LLMRouter:
    """Routes prompts to configured provider with payload sanitization."""

    def __init__(self, config: SecureConfig | None = None):
        self.config = config or SecureConfig.from_env()
        provider = self.config.llm_provider
        if provider == "openai":
            self._provider: _BaseProvider = _OpenAIProvider(self.config)
        elif provider == "anthropic":
            self._provider = _AnthropicProvider(self.config)
        elif provider == "ollama":
            self._provider = _OllamaProvider(self.config)
        elif provider == "rules":
            self._provider = _RulesProvider(self.config)
        elif provider == "cpu":
            self._provider = _CPUProvider(self.config)
        else:
            raise ValueError(
                f"Unsupported LLM_PROVIDER='{provider}'. "
                "Expected one of: rules, cpu, openai, anthropic, ollama"
            )

    async def chat(
        self, *, system_prompt: str, user_payload: Any, model: str | None = None
    ) -> LLMResponsePayload:
        selected_model = model or self.config.llm_model
        payload = user_payload
        if self.config.sanitize_llm_payloads:
            payload = sanitize_for_llm(payload, max_chars=self.config.max_prompt_chars)

        if not isinstance(payload, str):
            import json

            payload_text = json.dumps(payload, ensure_ascii=True)
        else:
            payload_text = payload

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": payload_text},
        ]
        text = await self._provider.complete(messages, model=selected_model)
        return LLMResponsePayload.model_validate(
            {
                "provider": self.config.llm_provider,
                "model": selected_model,
                "text": text,
            }
        )
