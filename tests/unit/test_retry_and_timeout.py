import time
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.exceptions import ToolTimeoutError
from app.tools.base import BaseTool, ToolContext
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry


class EmptyInput(BaseModel):
    pass


class SimpleOutput(BaseModel):
    ok: bool


class FlakyTool(BaseTool[EmptyInput, SimpleOutput]):
    name = "flaky"
    description = "fails once"
    input_model = EmptyInput
    output_model = SimpleOutput
    max_retries = 2
    calls = 0

    def execute(self, db: Session, args: EmptyInput, context: ToolContext) -> SimpleOutput:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("transient")
        return SimpleOutput(ok=True)


class SlowTool(BaseTool[EmptyInput, SimpleOutput]):
    name = "slow"
    description = "exceeds timeout"
    input_model = EmptyInput
    output_model = SimpleOutput
    max_retries = 0
    timeout_seconds = 0.01

    def execute(self, db: Session, args: EmptyInput, context: ToolContext) -> SimpleOutput:
        time.sleep(0.02)
        return SimpleOutput(ok=True)


def test_transient_tool_failure_retries(db):
    registry = ToolRegistry()
    tool = FlakyTool()
    registry.register(tool)
    result = ToolExecutor(registry).execute(db, "flaky", {}, ToolContext(run_id="r", step_number=1))
    assert result.output == {"ok": True}
    assert result.retries == 1
    assert tool.calls == 2


def test_timeout_budget_is_enforced(db):
    registry = ToolRegistry()
    registry.register(SlowTool())
    try:
        ToolExecutor(registry).execute(db, "slow", {}, ToolContext(run_id="r", step_number=1))
        assert False, "expected timeout"
    except ToolTimeoutError:
        pass
