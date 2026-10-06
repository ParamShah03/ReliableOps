from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class InvestigateRequest(BaseModel):
    model_name: str | None = None


class AgentRunRead(BaseModel):
    id: str
    incident_id: str
    status: str
    current_step: int
    started_at: datetime | None
    completed_at: datetime | None
    model_name: str
    final_report: dict[str, Any] | None
    failure_reason: str | None
    model_config = ConfigDict(from_attributes=True)


class AgentStepRead(BaseModel):
    id: str
    run_id: str
    step_number: int
    step_type: str
    reasoning_summary: str
    tool_name: str | None
    tool_input: dict[str, Any] | None
    tool_output: dict[str, Any] | None
    status: str
    latency_ms: float | None
    retry_count: int
    error_message: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
