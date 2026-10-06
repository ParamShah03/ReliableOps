import pytest
from pydantic import ValidationError
from app.agent.decisions import AgentDecisionAdapter


def test_malformed_llm_decision_is_rejected():
    malformed = {"action": "tool", "tool_name": "query_metrics"}
    with pytest.raises(ValidationError):
        AgentDecisionAdapter.validate_python(malformed)


def test_arbitrary_action_type_is_rejected():
    malicious = {"action": "shell", "command": "rm -rf /"}
    with pytest.raises(ValidationError):
        AgentDecisionAdapter.validate_python(malicious)
