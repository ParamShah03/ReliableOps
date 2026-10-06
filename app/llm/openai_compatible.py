from __future__ import annotations

import json
import time
from typing import Any

import httpx
from pydantic import TypeAdapter, ValidationError

from app.core.config import get_settings
from app.core.exceptions import StructuredOutputError
from app.llm.base import LLMResult


class OpenAICompatibleLLMClient:
    def __init__(self, model_name: str | None = None):
        self.settings = get_settings()
        self.model_name = model_name or self.settings.llm_model
        if not self.settings.llm_api_key:
            raise ValueError("LLM_API_KEY is required when LLM_PROVIDER=openai_compatible")

    def _request(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"}
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        with httpx.Client(timeout=self.settings.llm_timeout_seconds) as client:
            response = client.post(f"{self.settings.llm_base_url.rstrip('/')}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    def generate(self, prompt: str) -> str:
        data = self._request([{"role": "user", "content": prompt}])
        return data["choices"][0]["message"]["content"]

    def generate_structured(self, prompt: str, adapter: TypeAdapter, *, repair_hint: str | None = None) -> LLMResult:
        messages = [
            {
                "role": "system",
                "content": "Return ONLY one JSON object that matches the requested schema. Never include hidden chain-of-thought; provide concise decision summaries only.",
            },
            {"role": "user", "content": prompt},
        ]
        if repair_hint:
            messages.append({"role": "user", "content": f"Repair the response to satisfy validation: {repair_hint}"})

        start = time.perf_counter()
        last_error: Exception | None = None
        for attempt in range(self.settings.llm_max_retries + 1):
            try:
                data = self._request(messages)
                content = data["choices"][0]["message"]["content"]
                parsed = adapter.validate_python(json.loads(content))
                usage = data.get("usage") or {}
                return LLMResult(
                    data=parsed,
                    latency_ms=(time.perf_counter() - start) * 1000,
                    input_tokens=usage.get("prompt_tokens"),
                    output_tokens=usage.get("completion_tokens"),
                    retry_count=attempt,
                )
            except (json.JSONDecodeError, ValidationError, KeyError, httpx.HTTPError) as exc:
                last_error = exc
                messages.append({"role": "user", "content": f"Previous output was invalid: {exc}. Return corrected JSON only."})
                time.sleep(min(0.25 * (2**attempt), 1.0))
        raise StructuredOutputError(f"Structured generation failed: {last_error}")
