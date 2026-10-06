import pytest
from app.core.exceptions import ApprovalRequired
from app.tools.base import ToolContext
from app.tools.executor import ToolExecutor
from app.tools.factory import build_tool_registry


def test_risky_action_requires_approval(db):
    executor = ToolExecutor(build_tool_registry())
    with pytest.raises(ApprovalRequired) as exc:
        executor.execute(
            db,
            "rollback_deployment",
            {"service": "payment-service", "version": "v1.4.2"},
            ToolContext(run_id="run-x", step_number=7, approved=False),
        )
    assert exc.value.payload == {"service": "payment-service", "version": "v1.4.2"}
