from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import TypeAdapter


@dataclass
class LLMResult:
    data: Any
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    retry_count: int = 0
    validation_error: str | None = None


class LLMClient(Protocol):
    model_name: str

    def generate(self, prompt: str) -> str: ...

    def generate_structured(self, prompt: str, adapter: TypeAdapter, *, repair_hint: str | None = None) -> LLMResult: ...
