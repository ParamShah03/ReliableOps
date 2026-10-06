from typing import Any, Literal, Annotated
from pydantic import BaseModel, Field, TypeAdapter


class EvidenceItem(BaseModel):
    source: str
    detail: str
    step_number: int | None = None


class FinalReport(BaseModel):
    incident_summary: str
    root_cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_evidence: list[EvidenceItem]
    related_deployment: str | None = None
    recommended_actions: list[str]
    runbook_sources: list[str]


class ToolDecision(BaseModel):
    action: Literal["tool"]
    decision_summary: str
    reason: str
    tool_name: str
    tool_input: dict[str, Any]


class FinalizeDecision(BaseModel):
    action: Literal["finalize"]
    decision_summary: str
    reason: str
    report: FinalReport


AgentDecision = Annotated[ToolDecision | FinalizeDecision, Field(discriminator="action")]
AgentDecisionAdapter = TypeAdapter(AgentDecision)
