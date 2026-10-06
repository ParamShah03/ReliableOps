from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.enums import RiskLevel
from app.core.exceptions import ApprovalRequired, ToolExecutionError, ToolTimeoutError
from app.tools.base import ToolContext
from app.tools.registry import ToolRegistry


@dataclass
class ToolExecutionResult:
    output: dict[str, Any]
    latency_ms: float
    retries: int


class ToolExecutor:
    """Centralizes validation, policy, retries, timeout accounting and output validation.

    Built-in tools are local and synchronous. Each attempt is timed and treated as
    a timeout if it exceeds the declared budget. Real network-backed tools should
    also configure their transport-level timeout (e.g. httpx) so the underlying
    I/O is actively cancelled rather than only detected after return.
    """

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def execute(self, db: Session, tool_name: str, raw_input: dict[str, Any], context: ToolContext) -> ToolExecutionResult:
        tool = self.registry.get(tool_name)
        try:
            args = tool.validate_input(raw_input)
        except ValidationError as exc:
            raise ToolExecutionError(f"Invalid input for {tool_name}: {exc}") from exc

        if tool.risk_level == RiskLevel.REQUIRES_APPROVAL and not context.approved:
            raise ApprovalRequired(tool_name, args.model_dump(mode="json"))

        total_start = time.perf_counter()
        last_error: Exception | None = None
        for attempt in range(tool.max_retries + 1):
            attempt_start = time.perf_counter()
            try:
                output = tool.execute(db, args, context)
                elapsed = time.perf_counter() - attempt_start
                if elapsed > tool.timeout_seconds:
                    raise ToolTimeoutError(f"Tool {tool_name} exceeded timeout budget of {tool.timeout_seconds}s")
                validated = tool.output_model.model_validate(output)
                return ToolExecutionResult(
                    output=validated.model_dump(mode="json"),
                    latency_ms=(time.perf_counter() - total_start) * 1000,
                    retries=attempt,
                )
            except ToolTimeoutError as exc:
                last_error = exc
            except ToolExecutionError as exc:
                last_error = exc
            except Exception as exc:
                last_error = ToolExecutionError(f"Tool {tool_name} failed: {exc}")

            if attempt < tool.max_retries:
                time.sleep(min(0.1 * (2**attempt), 0.5))

        assert last_error is not None
        raise last_error
